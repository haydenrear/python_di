import uuid
from unittest import TestCase

import injector
from injector import Binder

from python_di.inject.composite_injector import CompositeInjector, CompositeScope


class TestOne:
    def __init__(self):
        self.test = str(uuid.uuid4())


class TestTwo:
    def __init__(self):
        self.test = str(uuid.uuid4())


class TestThree:
    def __init__(self):
        self.test = str(uuid.uuid4())


class TestFour:
    def __init__(self):
        self.test = str(uuid.uuid4())


class TestFive:
    def __init__(self):
        self.test = str(uuid.uuid4())


class TestMod(injector.Module):

    def configure(self, binder: Binder) -> None:
        binder.bind(TestOne, TestOne, scope=injector.singleton)
        binder.bind(TestTwo, TestTwo, scope=injector.singleton)
        binder.bind(TestThree, TestThree, scope=injector.singleton)


class TestModTwo(injector.Module):

    def configure(self, binder: Binder) -> None:
        binder.bind(TestThree, TestThree, scope=injector.singleton)
        binder.bind(TestFour, TestFour, scope=injector.singleton)


class TestModThree(injector.Module):

    def configure(self, binder: Binder) -> None:
        binder.bind(TestFour, TestFour, scope=injector.singleton)
        binder.bind(TestFive, TestFive, scope=injector.singleton)


class TestCompositeBinder(TestCase):
    def test_merge_with(self):
        created_one = CompositeInjector([TestMod])
        created_two = CompositeInjector([TestModTwo])
        child_two: CompositeInjector = created_one.create_child_injector(created_two)
        created_three = CompositeInjector([TestModThree])
        child_three: CompositeInjector = child_two.create_child_injector(created_three)
        found_four_eq = child_two.get(TestFour, injector.singleton)
        found_four = child_three.get(TestFour, injector.singleton)
        found_three = child_two.get(TestThree, injector.singleton)
        found_three_eq_again = child_three.get(TestThree, injector.singleton)
        found_three_eq = created_one.get(TestThree, injector.singleton)
        assert found_three_eq.test == found_three_eq_again.test
        assert found_four.test == found_four_eq.test
        assert found_three_eq.test == found_three.test

