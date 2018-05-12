import torch
from torch import nn
import torch.nn.functional as F
from torch.autograd import Variable


class NTM(nn.Module):
    def __init__(self, input_size, output_size, controller, memory, read_heads, write_heads):
        super(NTM, self).__init__()
        self.input_size = input_size
        self.output_size = output_size
        self.controller = controller
        self.memory = memory
        self.read_heads = read_heads
        self.write_heads = write_heads

        _, M = memory.size()

        self.output_fc = nn.Linear(controller.output_size + M, output_size)
        self.reset_params()

    def reset_params(self):
        # Initialize the linear layer
        nn.init.xavier_uniform(self.fc.weight, gain=1)
        nn.init.normal(self.fc.bias, std=0.01)

    def forward(self, inp, prev_reads, prev_controller_state, prev_ws):
        controller_outs, controller_states = self.controller(torch.cat([inp] + prev_reads, dim=1),
                                                             prev_controller_state)

        weights = []

        reads = []
        for prev_w, head in zip(prev_ws[:len(self.read_heads)], self.read_heads):
            params = head(controller_outs)
            weight = self.memory.address(prev_w, *params)
            weights.append(weight)
            read_vec = self.memory.read(weight)
            reads.append(read_vec)

        for prev_w, head in zip(prev_ws[len(self.read_heads):], self.write_heads):
            params = head(controller_outs)
            addr_params, e, a = params
            weight = self.memory.address(prev_w, *addr_params)
            weights.append(weight)
            self.memory.write(weight, e, a)

        out = F.sigmoid(self.output_fc(torch.cat([controller_outs] + reads)))

        return out, reads, controller_states, weights