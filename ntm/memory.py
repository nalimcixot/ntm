import torch
from torch import nn
import torch.nn.functional as F
import numpy as np


class Memory(nn.Module):
    def __init__(self, N, M):
        # N: # of words
        # M: word length
        super(Memory, self).__init__()

        self.N = N
        self.M = M
        self.mem_bias = torch.Tensor(N, M)
        # self.register_buffer('mem_bias', torch.Tensor(N, M))

        # Initialize memory bias
        stdev = 1 / (np.sqrt(N + M))
        nn.init.uniform_(self.mem_bias, -stdev, stdev)

    def reset(self, batch_size):
        self.batch_size = batch_size
        self.memory = self.mem_bias.clone().repeat(batch_size, 1, 1)

    def size(self):
        return self.N, self.M

    def read(self, w):
        return (w.unsqueeze(2) * self.memory).sum(1)

    def write(self, w, e, a):
        self.memory = self.memory * (1 - w.unsqueeze(-1) @ e.unsqueeze(1))
        self.memory = self.memory + w.unsqueeze(-1) @ a.unsqueeze(1)

    def address(self, prev_w, k, beta, g, s, y):
        wc = self.content_address(k, beta)
        wg = self.interpolation(prev_w, wc, g)
        wt = self.conv_shift(wg, s)
        return self.sharpen(wt, y)

    def content_address(self, k, beta):
        t = F.cosine_similarity(k.unsqueeze(1), self.memory, dim=-1)
        return F.softmax(beta * t, dim=1)

    def interpolation(self, prev_w, wc, g):
        return g * wc + (1 - g) * prev_w

    def conv_shift(self, wg, s):
        padding_size = s.size()[1] // 2
        padded_wg = torch.cat([wg[:, -padding_size:], wg, wg[:, :padding_size]], dim=1)

        result = torch.zeros(wg.size())

        for b in range(self.batch_size):
            result[b] = F.conv1d(padded_wg[b].view(1, 1, -1), s[b].view(1, 1, -1)).view(-1)

        return result

    def sharpen(self, wt, y):
        wt = wt ** y
        s = wt.sum(dim=1).unsqueeze(-1)
        return wt / s
