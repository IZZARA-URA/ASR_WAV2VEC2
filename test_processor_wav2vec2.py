
import json
import os
import shutil
import tempfile
import unittest

from utils import FEATURE_EXTRACTOR_NAME
from wav2vec2CTCTokenizer import VOCAB_FILES_NAMES

from wav2vec2CTCTokenizer import Wav2Vec2CTCTokenizer
from wav2vec2FeatureExtractor import Wav2Vec2FeatureExtractor
from wav2vec2Processor import Wav2Vec2Processor

from test_feature_extraction_wav2vec2 import floats_list


class Wav2Vec2ProcessorTest(unittest.TestCase):
    def setUp(self):
        vocab = "<pad> <s> </s> <unk> | E T A O N I H S R D L U M W C F G Y P B V K ' X J Q Z".split(" ")
        vocab_tokens = dict(zip(vocab, range(len(vocab))))

        self.add_kwargs_tokens_map = {
            "pad_token": "<pad>",
            "unk_token": "<unk>",
            "bos_token": "<s>",
            "eos_token": "</s>",
        }
        feature_extractor_map = {
            "feature_size": 1,
            "padding_value": 0.0,
            "sampling_rate": 16000,
            "return_attention_mask": False,
            "do_normalize": True,
        }

        self.tmpdirname = tempfile.mkdtemp()
        self.vocab_file = os.path.join(self.tmpdirname, VOCAB_FILES_NAMES["vocab_file"])
        self.feature_extraction_file = os.path.join(self.tmpdirname, FEATURE_EXTRACTOR_NAME)
        with open(self.vocab_file, "w", encoding="utf-8") as fp:
            fp.write(json.dumps(vocab_tokens) + "\n")

        with open(self.feature_extraction_file, "w", encoding="utf-8") as fp:
            fp.write(json.dumps(feature_extractor_map) + "\n")

    def get_tokenizer(self, **kwargs):
        kwargs.update(self.add_kwargs_tokens_map)
        return Wav2Vec2CTCTokenizer.from_pretrained(self.tmpdirname, **kwargs)

    def get_feature_extractor(self, **kwargs):
        return Wav2Vec2FeatureExtractor.from_pretrained(self.tmpdirname, **kwargs)

    def tearDown(self):
        shutil.rmtree(self.tmpdirname)

    def test_save_load_pretrained_default(self):
        tokenizer = self.get_tokenizer()
        feature_extractor = self.get_feature_extractor()

        processor = Wav2Vec2Processor(tokenizer=tokenizer, feature_extractor=feature_extractor)

        processor.save_pretrained(self.tmpdirname)
        processor = Wav2Vec2Processor.from_pretrained(self.tmpdirname)

        self.assertEqual(processor.tokenizer.get_vocab(), tokenizer.get_vocab())
        self.assertIsInstance(processor.tokenizer, Wav2Vec2CTCTokenizer)

        self.assertEqual(processor.feature_extractor.to_json_string(), feature_extractor.to_json_string())
        self.assertIsInstance(processor.feature_extractor, Wav2Vec2FeatureExtractor)

    def test_save_load_pretrained_additional_features(self):
        processor = Wav2Vec2Processor(tokenizer=self.get_tokenizer(), feature_extractor=self.get_feature_extractor())
        processor.save_pretrained(self.tmpdirname)

        tokenizer_add_kwargs = self.get_tokenizer(bos_token="(BOS)", eos_token="(EOS)")
        feature_extractor_add_kwargs = self.get_feature_extractor(do_normalize=False, padding_value=1.0)

        processor = Wav2Vec2Processor.from_pretrained(
            self.tmpdirname, bos_token="(BOS)", eos_token="(EOS)", do_normalize=False, padding_value=1.0
        )

        self.assertEqual(processor.tokenizer.get_vocab(), tokenizer_add_kwargs.get_vocab())
        self.assertIsInstance(processor.tokenizer, Wav2Vec2CTCTokenizer)

        self.assertEqual(processor.feature_extractor.to_json_string(), feature_extractor_add_kwargs.to_json_string())
        self.assertIsInstance(processor.feature_extractor, Wav2Vec2FeatureExtractor)

    def test_feature_extractor(self):
        feature_extractor = self.get_feature_extractor()
        tokenizer = self.get_tokenizer()

        processor = Wav2Vec2Processor(tokenizer=tokenizer, feature_extractor=feature_extractor)

        raw_speech = floats_list((3, 1000))

        input_feat_extract = feature_extractor(raw_speech, return_tensors="np")
        input_processor = processor(raw_speech, return_tensors="np")

        for key in input_feat_extract.keys():
            self.assertAlmostEqual(input_feat_extract[key].sum(), input_processor[key].sum(), delta=1e-2)

    def test_tokenizer(self):
        feature_extractor = self.get_feature_extractor()
        tokenizer = self.get_tokenizer()

        processor = Wav2Vec2Processor(tokenizer=tokenizer, feature_extractor=feature_extractor)

        input_str = "This is a test string"

        with processor.as_target_processor():
            encoded_processor = processor(input_str)

        encoded_tok = tokenizer(input_str)

        for key in encoded_tok.keys():
            self.assertListEqual(encoded_tok[key], encoded_processor[key])

    def test_tokenizer_decode(self):
        feature_extractor = self.get_feature_extractor()
        tokenizer = self.get_tokenizer()

        processor = Wav2Vec2Processor(tokenizer=tokenizer, feature_extractor=feature_extractor)

        predicted_ids = [[1, 4, 5, 8, 1, 0, 8], [3, 4, 3, 1, 1, 8, 9]]

        decoded_processor = processor.batch_decode(predicted_ids)
        decoded_tok = tokenizer.batch_decode(predicted_ids)

        self.assertListEqual(decoded_tok, decoded_processor)
