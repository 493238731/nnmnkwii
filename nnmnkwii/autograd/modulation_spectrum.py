from __future__ import with_statement, print_function, absolute_import

from torch.autograd import Function
import torch
import numpy as np


class ModulationSpectrum(Function):
    """Modulation spectrum computation

    f : (T, D) -> (N//2+1, D).

    where `N` is the DFT length.
    """

    def __init__(self, n=2048, norm=None):
        self.n = n
        self.norm = norm

    def forward(self, y):
        assert y.dim() == 2
        self.save_for_backward(y)

        T, D = y.size()
        y_np = y.numpy()

        s_complex = np.fft.rfft(y_np, n=self.n, axis=0,
                                norm=self.norm)  # DFT against time axis
        assert s_complex.shape == (self.n // 2 + 1, D)
        R, I = s_complex.real, s_complex.imag
        ms = torch.from_numpy(R * R + I * I)

        return ms

    def backward(self, grad_output):
        y, = self.saved_tensors
        T, D = y.size()
        assert grad_output.size() == torch.Size((self.n // 2 + 1, D))

        y_np = y.numpy()
        kt = -2 * np.pi / self.n * np.arange(self.n // 2 +
                                             1)[:, None] * np.arange(T)

        assert kt.shape == (self.n // 2 + 1, T)
        cos_table = np.cos(kt)
        sin_table = np.sin(kt)

        R = np.zeros((self.n // 2 + 1, D))
        I = np.zeros((self.n // 2 + 1, D))
        s_complex = np.fft.rfft(y_np, n=self.n, axis=0,
                                norm=self.norm)  # DFT against time axis
        assert s_complex.shape == (self.n // 2 + 1, D)
        R, I = s_complex.real, s_complex.imag

        grads = torch.zeros(T, D)
        C = 2  # normalization constant
        if self.norm == "ortho":
            C /= np.sqrt(T)  # np.sqrt(self.n)

        for d in range(D):
            r = R[:, d][:, None]
            i = I[:, d][:, None]
            grad = C * (r * cos_table + i * sin_table)
            assert grad.shape == sin_table.shape
            grads[:, d] = torch.from_numpy(
                grad_output[:, d].numpy().T.dot(grad))

        return grads


def modspec(y, n=2048, norm=None):
    return ModulationSpectrum(n=n, norm=norm)(y)
