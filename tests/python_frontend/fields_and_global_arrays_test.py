# Copyright 2019-2021 ETH Zurich and the DaCe authors. All rights reserved.
""" Tests class fields and external arrays. """
import dace
import numpy as np
from dataclasses import dataclass
import pytest


def test_external_ndarray_readonly():
    A = np.random.rand(20)

    @dace.program
    def exttest_readonly():
        return A + 1

    assert np.allclose(exttest_readonly(), A + 1)


def test_external_ndarray_modify():
    A = np.random.rand(20)

    @dace.program
    def exttest_modify():
        A[:] = 1

    exttest_modify()
    assert np.allclose(A, 1)


def test_external_dataclass():
    @dataclass
    class MyObject:
        my_a: dace.float64[20]

    dc = MyObject(np.random.rand(20))

    @dace.program
    def exttest():
        dc.my_a[:] = 5

    exttest()
    assert np.allclose(dc.my_a, 5)


def test_dataclass_method():
    @dataclass
    class MyObject:
        my_a: dace.float64[20]

        def __init__(self) -> None:
            self.my_a = np.random.rand(20)

        @dace.method
        def something(self, B: dace.float64[20]):
            self.my_a += B

    dc = MyObject()
    acopy = np.copy(dc.my_a)
    b = np.random.rand(20)
    dc.something(b)
    assert np.allclose(dc.my_a, acopy + b)


def test_object_method():
    """ JIT-based inference of fields at call time. """
    class MyObject:
        def __init__(self) -> None:
            self.my_a = np.random.rand(20)

        @dace.method
        def something(self, B: dace.float64[20]):
            self.my_a += B

    obj = MyObject()
    acopy = np.copy(obj.my_a)
    b = np.random.rand(20)
    obj.something(b)
    assert np.allclose(obj.my_a, acopy + b)


def test_object_newfield():
    # This syntax (adding new fields at dace.method runtime) is disallowed
    with pytest.raises(SyntaxError):

        class MyObject:
            @dace.method
            def something(self, B: dace.float64[20]):
                self.my_newfield = B

        obj = MyObject()
        b = np.random.rand(20)
        obj.something(b)
        assert np.allclose(obj.my_newfield, b)


def test_object_constant():
    class MyObject:
        q: dace.constant

        def __init__(self) -> None:
            self.q = 5

        @dace.method
        def something(self, B: dace.float64[20]):
            return B + self.q

    obj = MyObject()
    A = np.random.rand(20)
    B = obj.something(A)
    assert np.allclose(B, A + 5)

    # Ensure constant was folded
    assert 'q' not in obj.something.to_sdfg().generate_code[0]


def test_external_cache():
    """ 
    If data descriptor changes from compile time to call time, warn and 
    recompile.
    """
    A = np.random.rand(20)

    @dace.program
    def plusglobal(B):
        return A + B

    B = np.random.rand(20)
    assert np.allclose(plusglobal(B), A + B)

    # Now modify the global
    A = np.random.rand(30)
    B = np.random.rand(30)
    assert np.allclose(plusglobal(B), A + B)


def test_nested_objects():
    """ Multiple objects with multiple "self" values and same field names. """
    class ObjA:
        def __init__(self, q) -> None:
            self.q = np.full([20], q)

        @dace.method
        def nested(self, A):
            return A + self.q

    class ObjB:
        def __init__(self, q) -> None:
            self.q = np.full([20], q)
            self.obja = ObjA(q * 2)

        @dace.method
        def outer(self, A):
            return A + self.q + self.obja.nested(A)

    A = np.random.rand(20)
    obj = ObjB(5)
    expected = A + obj.q + A + (obj.q * 2)

    result = obj.outer(A)
    assert np.allclose(expected, result)


def test_same_field_different_classes():
    """ 
    Testing for correctness in the existence of the same object in multiple
    contexts.
    """
    class A:
        def __init__(self, arr) -> None:
            self.arr = arr

    class B(A):
        def __init__(self, arr) -> None:
            super().__init__(arr)
            self.arr2 = arr

        @dace.method
        def mymethod(self, A):
            self.arr[:] = 1
            self.arr2[:] = A

    field = np.random.rand(20)
    param = np.random.rand(20)
    obj = B(field)
    obj.mymethod(param)
    assert np.allclose(obj.arr, param)


if __name__ == '__main__':
    test_external_ndarray_readonly()
    test_external_ndarray_modify()
    test_external_dataclass()
    test_dataclass_method()
    test_object_method()
    test_object_newfield()
    test_object_constant()
    test_external_cache()
    test_nested_objects()
    test_same_field_different_classes()