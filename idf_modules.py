'''
idf_modules.py - collects the modules that work on IDF files.
'''
from vistrails.core.modules.vistrails_module import NotCacheable, Module, Constant
import vistrails.core.modules.basic_modules as basic

class Idf(NotCacheable, Module):
    '''
    Wraps an eppy IDF3 object for use in the VisTrails system.

    The main problem we have here is that we need an IDD file
    to create an `IDF3` object. An we thus cannot provide a default
    value for Idf... that is why we don't inherit from `Constant`.
    '''
    _input_ports = [
        ('idf', basic.Path),
        ('idd', basic.Path),
    ]

    _output_ports = [('idf', basic.String)]

    def compute(self):
        from eppy.modeleditor import IDF, IDDAlreadySetError
        from StringIO import StringIO
        logger = logging.getLogger('UMEM.AddOutputVariable')

        idf_as_string = self.getInputFromPort('idf')
        key = self.getInputFromPort('key')
        variable = self.getInputFromPort('variable')
        frequency = self.getInputFromPort('frequency')
        idd_path = self.getInputFromPort('idd_path')

        logger.info('key=%s', key)
        logger.info('variable=%s', variable)
        logger.info('frequency=%s', frequency)
        logger.info('idd_path=%s', idd_path.name)

        try:
            IDF.setiddname(idd_path.name)
        except IDDAlreadySetError:
            pass

        idf = IDF(StringIO(idf_as_string))

        output_variable = idf.newidfobject('OUTPUT:VARIABLE')
        output_variable.Key_Value = key
        output_variable.Variable_Name = variable
        output_variable.Reporting_Frequency = frequency

        # output the result
        self.setResult('idf', idf.idfstr())
