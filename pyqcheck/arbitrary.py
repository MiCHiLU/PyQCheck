# -*- coding:utf-8 -*-

from importlib import import_module
import sys
import re
import traceback
import marshal

from util import print_results

class ArbitraryAbstraction(object):
  def __init__(self):
    pass

  def generate(self):
    raise NoImplementedError("Should extends use only this class.")

class ArbitraryList(list):
  def __init__(self, *args):
    for arg in args:
      self.append(arg)

  def __getattr__(self, name):
    return {
      "label": self[0],
      "func_name": self[1],
      "func_code": self[2],
      "success": self[3],
      "failure": self[4],
      "exceptions": self[5],
      "verbose": self[6]
    }.get(name)

class Arbitrary(object):
  '''
  Arbitrary is returned specified object.
  '''
  TEST_COUNT = 15

  def __init__(self, *args, **kwargs):
    self.arbitraries = args
    self.test_result = []

  def __get_arbitrary_content(self, arbitrary):
    if isinstance(arbitrary, str):
      module_filename = 'pq_' + arbitrary.lower()
      klass = 'PyQ' + arbitrary.title()
      module = import_module(
        'pyqcheck.arbitraries.' + module_filename
      )
      return getattr(module, klass)()

    if isinstance(arbitrary, ArbitraryAbstraction):
      return arbitrary

  def generate_arbitraries(self):
    arbitraries = []

    for arbitrary in self.arbitraries:
      if isinstance(arbitrary, tuple):
        arbitrary_name = arbitrary[0]
        arbitrary_limit = arbitrary[1]
      else:
        arbitrary_name = arbitrary
        arbitrary_limit = {}

      ar = self.__get_arbitrary_content(arbitrary_name)
      arbitraries.append(ar.generate(**arbitrary_limit))

    return arbitraries

  def property(self, label, func, *exception, **kwargs):
    self.label = label
    self.func = func
    self.exception = exception
    self.type_of_return_value = kwargs.get('type')

    return self

  def execute(self):
    label, func, exception = self.label, self.func, self.exception
    count = self.count if self.count >= 1 else Arbitrary.TEST_COUNT
    exceptions = {}
    verbose = []
    success, failure = 0,0

    for i in range(count):
      try:
        arbitraries = [f() for f in self.generate_arbitraries()]

        if len(arbitraries) == 1:
          try:
            verbose_valiable = '(' + str(arbitraries[0]) + ')'
          except UnicodeEncodeError, error:
            verbose_valiable = u'(' + arbitraries[0] + u')'
        else:
          try:
            verbose_valiable = str(tuple(arbitraries))
          except UnicodeEncodeError, error:
            verbose_valiable = unicode(tuple(arbitraries))

        verbose_valiable = verbose_valiable.encode('utf8')
        result = func(*arbitraries)

        if self.type_of_return_value:
          is_valid = isinstance(result, self.type_of_return_value)
        else:
          is_valid = result

        success = success + 1 if is_valid else success
        failure = failure + 1 if not is_valid else failure
        icon = u'\u2600' if is_valid else u'\u2601'

        if self.verbose:
          verbose.append(
            icon.encode('utf8') + '  ' +
            func.func_name + verbose_valiable
          )

      except exception, error:
        if self.verbose:
          verbose.append(u'\u2603'.encode('utf8') + '  ' + 
            func.func_name + verbose_valiable
          )

        exception_key = re.match('^([a-zA-Z]+)\(.*$', repr(error)).group(1)
        exceptions.setdefault(exception_key, 0)
        exceptions[exception_key] += 1

    return [
             label,
             func.func_name,
             marshal.dumps(func.func_code),
             success,
             failure,
             exceptions,
             verbose
           ]

  def run(self, count=15, verbose=False, queue=None):
    self.count = count
    self.verbose = verbose

    try:
      test_result = self.execute()
      if queue is not None:
        queue.put(test_result)

      self.test_result = ArbitraryList(*test_result)
      return self

    except TypeError as error:
      print('TypeError! please check into function valiables.')
      print(error.message)
      sys.exit(0)

    except ImportError as error:
      print('ImportError! ' + 
            'please check import module name or module file-path.')
      print(error.message)
      sys.exit(0)

    except Exception, error:
      print('!!! Exclude Error !!!')
      print(error.message)
      exc_type, exc_vlaue, exc_traceback = sys.exc_info()
      traceback.print_tb(exc_traceback, limit=10, file=sys.stdout)
      sys.exit(0)

  def result(self):
    print_results([self.test_result])
