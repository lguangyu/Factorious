#!/usr/bin/env python3

#import collections as _collections_m_
import numbers as _numbers_m_


class TextLabelEncoder(object):
	"""
	encode text labels into 0-based integers
	"""
	# encoding/decoding lambda expression
	_encoding_ = lambda x: None
	_decoding_ = lambda x: None


	def __init__(self) -> None:
		super(TextLabelEncoder, self).__init__()
		self._encode_dict = {}
		self._decode_list = {}
		self._encoding_ = lambda x: self._encode_dict[x]
		self._decoding_ = lambda x: self._decode_list[x]
		return


	def __len__(self):
		return len(self._decode_list)


	def __iter__(self):
		return iter(self._decode_list)


	def reset(self) -> None:
		"""
		reset trained maps
		"""
		self._encode_dict.clear()
		self._decode_list.clear()
		return


	def train(self,
			labels: list,
		) -> None:
		"""
		train the encoder by providing a list of labels,
		each label must be str;
		training will reset previous results

		PARAMETERS
		----------
		labels: a list of str instances

		EXCEPTIONS
		----------
		TypeError: if any label misses the expected type
		"""
		self.reset()
		labels = list(labels)
		res = [isinstance(i, str) for i in labels]
		if not all(res):
			raise TypeError("each label must be of type 'str'")
		# fill in encode/decode search tables
		self._decode_list = sorted(labels)
		self._encode_dict = {v: i for i, v in enumerate(self._decode_list)}
		return


	def encode(self,
			labels: list,
		) -> int or list:
		"""
		encode the input labels

		PARAMETERS
		----------
		labels: list of labels to be encoded;

		RETURNS
		-------
		list of encoded ids;
		"""
		return [self._encoding_(i) for i in labels]


	def decode(self,
			label_ids: list,
		) -> str or list:
		"""
		decode the input label ids to original labels

		PARAMETERS
		----------
		label_ids: list of label ids to be decoded

		RETURNS
		-------
		list of decoded labels
		"""
		return [self._decoding_(i) for i in label_ids]
