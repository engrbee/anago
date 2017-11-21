import os

from anago.data.preprocess import prepare_preprocessor, WordPreprocessor, filter_embeddings
from anago.models import SeqLabeling
from anago.trainer import Trainer
from anago.evaluator import Evaluator
from anago.tagger import Tagger
from anago.config import ModelConfig, TrainingConfig


class Sequence(object):

    config_file = 'config.json'
    weight_file = 'model_weights.h5'
    preprocessor_file = 'preprocessor.pkl'

    def __init__(self, char_emb_size=25, word_emb_size=100, char_lstm_units=25,
                 word_lstm_units=100, dropout=0.5, char_feature=True, crf=True,
                 batch_size=20, optimizer='adam', learning_rate=0.001, lr_decay=0.9,
                 clip_gradients=5.0, max_epoch=15, early_stopping=True, patience=3,
                 train_embeddings=True, max_checkpoints_to_keep=5, log_dir=None,
                 embeddings=()):

        self.model_config = ModelConfig(char_emb_size, word_emb_size, char_lstm_units,
                                        word_lstm_units, dropout, char_feature, crf)
        self.training_config = TrainingConfig(batch_size, optimizer, learning_rate,
                                              lr_decay, clip_gradients, max_epoch,
                                              early_stopping, patience, train_embeddings,
                                              max_checkpoints_to_keep)
        self.model = None
        self.p = None
        self.log_dir = log_dir
        self.embeddings = embeddings

    def train(self, x_train, y_train, x_valid=None, y_valid=None):
        self.p = prepare_preprocessor(x_train, y_train)
        embeddings = filter_embeddings(self.embeddings, self.p.vocab_word,
                                       self.model_config.word_embedding_size)
        self.model_config.char_vocab_size = len(self.p.vocab_char)

        self.model = SeqLabeling(self.model_config, embeddings, len(self.p.vocab_tag))

        trainer = Trainer(self.model,
                          self.training_config,
                          checkpoint_path=self.log_dir,
                          preprocessor=self.p)
        trainer.train(x_train, y_train, x_valid, y_valid)

    def eval(self, x_test, y_test):
        if self.model:
            evaluator = Evaluator(self.model, preprocessor=self.p)
            evaluator.eval(x_test, y_test)
        else:
            raise (OSError('Could not find a model. Call load(dir_path).'))

    def analyze(self, sent):
        if self.model:
            tagger = Tagger(self.model, preprocessor=self.p)
            return tagger.analyze(sent)
        else:
            raise (OSError('Could not find a model. Call load(dir_path).'))

    def save(self, dir_path):
        self.p.save(os.path.join(dir_path, self.preprocessor_file))
        self.model_config.save(os.path.join(dir_path, self.config_file))
        self.model.save(os.path.join(dir_path, self.weight_file))

    @classmethod
    def load(cls, dir_path):
        cls.p = WordPreprocessor.load(os.path.join(dir_path, cls.preprocessor_file))
        config = ModelConfig.load(os.path.join(dir_path, cls.config_file))
        cls.model = SeqLabeling(config, ntags=len(cls.p.vocab_tag))
        cls.model.load(filepath=os.path.join(dir_path, cls.weight_file))
