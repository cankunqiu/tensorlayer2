#! /usr/bin/python
# -*- coding: utf-8 -*-

import tensorflow as tf

from tensorlayer.layers.core import Layer

from tensorlayer.layers.utils import compute_deconv2d_output_shape

from tensorlayer.layers.convolution.expert_conv import Conv1dLayer

from tensorlayer.decorators import deprecated_alias
from tensorlayer.decorators import force_return_self

__all__ = [
    'AtrousConv1dLayer',
    'AtrousConv2dLayer',
    'AtrousDeConv2dLayer',
]


@deprecated_alias(layer='prev_layer', end_support_version="2.0.0")  # TODO: remove this line before releasing TL 2.0.0
def atrous_conv1d(
        prev_layer,
        n_filter=32,
        filter_size=2,
        stride=1,
        dilation=1,
        padding='SAME',
        data_format='NWC',
        W_init=tf.truncated_normal_initializer(stddev=0.02),
        b_init=tf.constant_initializer(value=0.0),
        W_init_args=None,
        b_init_args=None,
        act=None,
        name='atrous_1d',
):
    """Simplified version of :class:`AtrousConv1dLayer`.

    Parameters
    ----------
    prev_layer : :class:`Layer`
        Previous layer.
    n_filter : int
        The number of filters.
    filter_size : int
        The filter size.
    stride : tuple of int
        The strides: (height, width).
    dilation : int
        The filter dilation size.
    act : activation function
        The activation function of this layer.
    padding : str
        The padding algorithm type: "SAME" or "VALID".
    data_format : str
        Default is 'NWC' as it is a 1D CNN.
    W_init : initializer
        The initializer for the weight matrix.
    b_init : initializer or None
        The initializer for the bias vector. If None, skip biases.
    W_init_args : dictionary
        The arguments for the weight matrix initializer.
    b_init_args : dictionary
        The arguments for the bias vector initializer.
    name : str
        A unique layer name.

    Returns
    -------
    :class:`Layer`
        A :class:`AtrousConv1dLayer` object

    """
    return Conv1dLayer(
        prev_layer=prev_layer,
        act=act,
        shape=(filter_size, int(prev_layer.outputs.get_shape()[-1]), n_filter),
        stride=stride,
        padding=padding,
        dilation_rate=dilation,
        data_format=data_format,
        W_init=W_init,
        b_init=b_init,
        W_init_args=W_init_args,
        b_init_args=b_init_args,
        name=name,
    )


class AtrousConv2dLayer(Layer):
    """The :class:`AtrousConv2dLayer` class is 2D atrous convolution (a.k.a. convolution with holes or dilated
    convolution) 2D layer, see `tf.nn.atrous_conv2d <https://www.tensorflow.org/versions/master/api_docs/python/nn.html#atrous_conv2d>`__.

    Parameters
    ----------
    prev_layer : :class:`Layer`
        Previous layer with a 4D output tensor in the shape of (batch, height, width, channels).
    n_filter : int
        The number of filters.
    filter_size : tuple of int
        The filter size: (height, width).
    rate : int
        The stride that we sample input values in the height and width dimensions.
        This equals the rate that we up-sample the filters by inserting zeros across the height and width dimensions.
        In the literature, this parameter is sometimes mentioned as input stride or dilation.
    act : activation function
        The activation function of this layer.
    padding : str
        The padding algorithm type: "SAME" or "VALID".
    W_init : initializer
        The initializer for the weight matrix.
    b_init : initializer or None
        The initializer for the bias vector. If None, skip biases.
    W_init_args : dictionary
        The arguments for the weight matrix initializer.
    b_init_args : dictionary
        The arguments for the bias vector initializer.
    name : str
        A unique layer name.

    """

    @deprecated_alias(
        layer='prev_layer', end_support_version="2.0.0"
    )  # TODO: remove this line before releasing TL 2.0.0
    def __init__(
            self, prev_layer=None, n_filter=32, filter_size=(3, 3), rate=2, padding='SAME',
            W_init=tf.truncated_normal_initializer(stddev=0.02), b_init=tf.constant_initializer(value=0.0),
            W_init_args=None, b_init_args=None, act=None, name='atrous_2d'
    ):

        padding = padding.upper()
        if padding not in ["SAME", "VALID"]:
            raise ValueError("`padding` value is not valid, should be either: 'SAME' or 'VALID'")

        self.prev_layer = prev_layer
        self.n_filter = n_filter
        self.filter_size = filter_size
        self.rate = rate
        self.padding = padding
        self.W_init = W_init
        self.b_init = b_init
        self.act = act
        self.name = name

        super(AtrousConv2dLayer, self).__init__(W_init_args=W_init_args, b_init_args=b_init_args)

    def __str__(self):
        additional_str = []

        try:
            additional_str.append("n_filter: %d" % self.n_filter)
        except AttributeError:
            pass

        try:
            additional_str.append("filter_size: %s" % str(self.filter_size))
        except AttributeError:
            pass

        try:
            additional_str.append("rate: %d" % self.rate)
        except AttributeError:
            pass

        try:
            additional_str.append("pad: %s" % self.pad)
        except AttributeError:
            pass

        try:
            additional_str.append("act: %s" % self.act.__name__ if self.act is not None else 'No Activation')
        except AttributeError:
            pass

        return self._str(additional_str)
    def compile(self, prev_layer, is_train=True):

        super(AtrousConv2dLayer, self).compile(prev_layer)

        with tf.variable_scope(self.name):
            shape = [self.filter_size[0], self.filter_size[1], int(self.inputs.get_shape()[-1]), self.n_filter]

            weight_matrix = self._get_tf_variable(
                name='W_atrous_conv2d', shape=shape, initializer=self.W_init, dtype=self.inputs.dtype,
                **self.W_init_args
            )

            self.outputs = tf.nn.atrous_conv2d(self.inputs, filters=weight_matrix, rate=self.rate, padding=self.padding)

            if self.b_init:
                b = self._get_tf_variable(
                    name='b_atrous_conv2d', shape=(self.n_filter, ), initializer=self.b_init, dtype=self.inputs.dtype,
                    **self.b_init_args
                )

                self.outputs = tf.nn.bias_add(self.outputs, b, name='bias_add')

            self.outputs = self._apply_activation(self.outputs)

        self._add_layers(self.outputs)
        self._add_params(self._local_weights)


class AtrousDeConv2dLayer(Layer):
    """The :class:`AtrousDeConv2dLayer` class is 2D atrous convolution transpose, see `tf.nn.atrous_conv2d_transpose <https://www.tensorflow.org/versions/master/api_docs/python/nn.html#atrous_conv2d_transpose>`__.

    Parameters
    ----------
    prev_layer : :class:`Layer`
        Previous layer with a 4D output tensor in the shape of (batch, height, width, channels).
    shape : tuple of int
        The shape of the filters: (filter_height, filter_width, out_channels, in_channels).
    output_shape : tuple of int
        Output shape of the deconvolution.
    rate : int
        The stride that we sample input values in the height and width dimensions.
        This equals the rate that we up-sample the filters by inserting zeros across the height and width dimensions.
        In the literature, this parameter is sometimes mentioned as input stride or dilation.
    act : activation function
        The activation function of this layer.
    padding : str
        The padding algorithm type: "SAME" or "VALID".
    W_init : initializer
        The initializer for the weight matrix.
    b_init : initializer or None
        The initializer for the bias vector. If None, skip biases.
    W_init_args : dictionary
        The arguments for the weight matrix initializer.
    b_init_args : dictionary
        The arguments for the bias vector initializer.
    name : str
        A unique layer name.

    """

    @deprecated_alias(
        layer='prev_layer', end_support_version="2.0.0"
    )  # TODO: remove this line before releasing TL 2.0.0
    def __init__(
            self, prev_layer=None, shape=(3, 3, 128, 256), rate=2, padding='SAME',
            W_init=tf.truncated_normal_initializer(stddev=0.02), b_init=tf.constant_initializer(value=0.0),
            W_init_args=None, b_init_args=None, act=None, name='atrous_2d_transpose'
    ):

        padding = padding.upper()
        if padding not in ["SAME", "VALID"]:
            raise ValueError("`padding` value is not valid, should be either: 'SAME' or 'VALID'")

        self.prev_layer = prev_layer
        self.shape = shape
        self.rate = rate
        self.padding = padding
        self.W_init = W_init
        self.b_init = b_init
        self.act = act
        self.name = name

        super(AtrousDeConv2dLayer, self).__init__(W_init_args=W_init_args, b_init_args=b_init_args)

    def __str__(self):
        additional_str = []

        try:
            additional_str.append("shape: %s" % str(self.shape))
        except AttributeError:
            pass

        try:
            additional_str.append("output_shape: %s" % str(self.out_shape))
        except AttributeError:
            pass

        try:
            additional_str.append("rate: %d" % self.rate)
        except AttributeError:
            pass

        try:
            additional_str.append("padding: %s" % self.padding)
        except AttributeError:
            pass

        try:
            additional_str.append("act: %s" % self.act.__name__ if self.act is not None else 'No Activation')
        except AttributeError:
            pass

        return self._str(additional_str)
    def compile(self, prev_layer, is_train=True):

        self._parse_inputs(prev_layer)

        with tf.variable_scope(self.name):
            weight_matrix = self._get_tf_variable(
                name='W_atrous_conv2d_transpose', shape=self.shape, initializer=self.W_init, dtype=self.inputs.dtype,
                **self.W_init_args
            )

            self.out_shape = compute_deconv2d_output_shape(
                self.inputs, self.shape[0], self.shape[1], 1, 1, self.shape[2], padding=self.padding, data_format="NHWC"
            )

            self.outputs = tf.nn.atrous_conv2d_transpose(
                self.inputs, filters=weight_matrix, output_shape=self.out_shape, rate=self.rate, padding=self.padding
            )

            if self.b_init:
                b = self._get_tf_variable(
                    name='b_atrous_conv2d_transpose', shape=(self.shape[-2]), initializer=self.b_init,
                    dtype=self.inputs.dtype, **self.b_init_args
                )

                self.outputs = tf.nn.bias_add(self.outputs, b, name='bias_add')

            self.outputs = self._apply_activation(self.outputs)
            #self.out_shape = self.outputs.shape

        super(AtrousDeConv2dLayer, self).compile(prev_layer)

        self._add_layers(self.outputs)
        self._add_params(self._local_weights)


# Alias
AtrousConv1dLayer = atrous_conv1d
