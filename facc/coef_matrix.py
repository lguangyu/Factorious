#!/usr/bin/env python3

from . import scipy_interface as _scipy_m_


class CoefficientMatrix(_scipy_m_.ndarray):
	#@staticmethod
	def __new__(cls, shape) -> None:
		"""
		PARAMETERS
		----------
		shape:
			shape of the matrix, i.e. #Recipes by #Items;
		"""
		self = super(CoefficientMatrix, cls).__new__(cls,
			shape, dtype = float)
		self.fill(0.0)
		return self
