# -*- coding: utf-8 -*-

import numpy as np
import torch as th
import torch.nn as nn

from leibniz.unet.warp import WarpLayer


class BasicBlock(nn.Module):
    def __init__(self, in_channel, out_channel, step, relu, conv, reduction=16):
        super(BasicBlock, self).__init__()
        self.step = step
        self.relu = relu

        self.conv1 = conv(in_channel, in_channel, kernel_size=3, stride=1, padding=1)
        self.conv2 = conv(in_channel, out_channel, kernel_size=3, stride=1, padding=1)
        self.warp = WarpLayer(out_channel)

    def forward(self, x):
        y = self.conv1(x)
        y = self.relu(y)
        y = self.conv2(y)
        y = self.warp(y)
        return y


class Bottleneck(nn.Module):
    def __init__(self, in_channel, out_channel, step, relu, conv, reduction=16):
        super(Bottleneck, self).__init__()
        self.step = step
        self.relu = relu

        self.conv1 = conv(in_channel, in_channel // 4, kernel_size=1, bias=False)
        self.conv2 = conv(in_channel // 4, in_channel // 4, kernel_size=3, bias=False, padding=1)
        self.conv3 = conv(in_channel // 4, out_channel, kernel_size=1, bias=False)
        self.warp = WarpLayer(out_channel)

    def forward(self, x):
        y = self.conv1(x)
        y = self.relu(y)
        y = self.conv2(y)
        y = self.relu(y)
        y = self.conv3(y)
        y = self.warp(y)
        return y


class HyperBasic(nn.Module):
    extension = 1
    least_required_dim = 1

    def __init__(self, dim, step, relu, conv, reduction=16):
        super(HyperBasic, self).__init__()
        self.dim = dim
        self.step = step

        self.input = BasicBlock(dim, 4 * dim, step, relu, conv, reduction=reduction)
        self.output = BasicBlock(8 * dim, dim, step, relu, conv, reduction=reduction)

    def forward(self, x):
        input = self.input(x)
        velo = input[:, 2 * self.dim:3 * self.dim]
        theta = input[:, 3 * self.dim:]

        cs = self.step * velo * th.cos(theta * np.pi * 6)
        ss = self.step * velo * th.sin(theta * np.pi * 6)

        y1 = (1 + ss) * x + cs
        y2 = (1 + cs) * x - ss
        y3 = (1 - cs) * x + ss
        y4 = (1 - ss) * x - cs
        ys = th.cat((y1, y2, y3, y4, input), dim=1)

        return x + self.output(ys)


class HyperBottleneck(nn.Module):
    extension = 4
    least_required_dim = 1

    def __init__(self, dim, step, relu, conv, reduction=16):
        super(HyperBottleneck, self).__init__()
        self.dim = dim
        self.step = step

        self.input = Bottleneck(dim, 4 * dim, step, relu, conv, reduction=reduction)
        self.output = Bottleneck(8 * dim, dim, step, relu, conv, reduction=reduction)

    def forward(self, x):
        input = self.input(x)
        velo = input[:, 2 * self.dim:3 * self.dim]
        theta = input[:, 3 * self.dim:]

        cs = self.step * velo * th.cos(theta * np.pi * 6)
        ss = self.step * velo * th.sin(theta * np.pi * 6)

        y1 = (1 + ss) * x + cs
        y2 = (1 + cs) * x - ss
        y3 = (1 - cs) * x + ss
        y4 = (1 - ss) * x - cs
        ys = th.cat((y1, y2, y3, y4, input), dim=1)

        return x + self.output(ys)
