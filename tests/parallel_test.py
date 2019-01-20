# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as onp
from absl.testing import absltest
from absl.testing import parameterized

import jax.numpy as np
from jax import test_util as jtu
from jax.api import pmap, papply, make_jaxpr
from jax.interpreters.parallel import psum

from jax.config import config
config.parse_flags_with_absl()


class PmapTest(jtu.JaxTestCase):

  def testConstantFunction(self):
    f = lambda x: 3
    ans = pmap(f, axis_name='i')(onp.ones(4))
    expected = 3 * onp.ones(4)
    self.assertAllClose(ans, expected, check_dtypes=False)

  def testReduceSum(self):
    f = lambda x: psum(x, 'i')
    ans = pmap(f, axis_name='i')(onp.ones(4))
    expected = 4 * onp.ones(4)
    self.assertAllClose(ans, expected, check_dtypes=False)

  def testLogSoftmax(self):

    def f(x):
      return x - np.log(psum(np.exp(x), 'i'))

    x = onp.log(onp.arange(1., 10., dtype=onp.float32))

    ans = pmap(f, axis_name='i')(x)
    expected = x - onp.log(onp.sum(onp.exp(x)))
    self.assertAllClose(ans, expected, check_dtypes=False)


class PapplyTest(jtu.JaxTestCase):

  def testIdentity(self):
    pfun, axis_name = papply(lambda x: x)
    ans = pfun(onp.arange(3))
    expected = onp.arange(3)
    self.assertAllClose(ans, expected, check_dtypes=False)

  def testMap(self):
    pfun, axis_name = papply(np.sin)
    ans = pfun(onp.arange(3.))
    expected = onp.sin(onp.arange(3.))
    self.assertAllClose(ans, expected, check_dtypes=False)

  def testSum(self):
    pfun, axis_name = papply(np.sum)

    jaxpr = make_jaxpr(pfun)(onp.zeros(5))
    expected_jaxpr = make_jaxpr(lambda x: psum(x, axis_name))(onp.zeros(5))
    assert repr(jaxpr) == repr(expected_jaxpr)

    ans = pmap(pfun, axis_name)(onp.arange(3.))
    expected = onp.sum(onp.arange(3.))
    self.assertAllClose(ans, expected, check_dtypes=False)

  def testLogSoftmax(self):

    def fun(x):
      return x - np.log(np.sum(np.exp(x)))

    pfun, axis_name = papply(fun)

    jaxpr = make_jaxpr(pfun)(onp.zeros(5))
    expected_jaxpr = make_jaxpr(lambda x: x - np.log(psum(np.exp(x), axis_name))
                                )(onp.zeros(5))
    assert repr(jaxpr) == repr(expected_jaxpr)

    ans = pmap(pfun, axis_name)(onp.arange(1., 5.))
    expected = fun(onp.arange(1., 5.))
    self.assertAllClose(ans, expected, check_dtypes=False)

  def testAdd(self):
    x = onp.array([[1, 2], [3, 4]])
    expected = x + x

    pfun, axis_name = papply(np.add)
    ans = pmap(pfun, axis_name)(x, x)
    self.assertAllClose(ans, expected, check_dtypes=True)

    pfun, axis_name = papply(np.add, (0, 1))
    ans = pmap(pfun, axis_name)(x, x)
    self.assertAllClose(ans, expected, check_dtypes=True)

    # TODO needs reshape papply rule
    # pfun, axis_name = papply(lambda y: y + x)
    # ans = pmap(pfun, axis_name)(x)
    # self.assertAllClose(ans, expected, check_dtypes=True)
    # ans = pmap(pfun, axis_name)(x)
    # self.assertAllClose(ans, expected, check_dtypes=True)


if __name__ == '__main__':
  absltest.main()
