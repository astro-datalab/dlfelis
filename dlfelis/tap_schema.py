# Licensed under a BSD-style 3-clause license - see LICENSE.md.
# -*- coding: utf-8 -*-
"""
dlfelis.tap_schema
==================

Tools for working with Astro Data Lab TapSchema_.

.. _TapSchema: https://github.com/astro-datalab/TapSchema
"""
# """
# Transform a TapSchema JSON file to felis/YAML.
# """
import argparse
import json
import os
import subprocess
import sys
import yaml

#
# Conversion between types used in TapSchema and types required by Felis.
#
felis_datatypes = {'bigint': 'long',
                   'integer': 'int',
                   'smallint': 'short',
                   'real': 'float',
                   'REAL': 'float',
                   'character': 'string',
                   'varchar': 'string'}
#
# Conversion between units used in TapSchema and units recommended by Felis,
# which adheres to the FITS standard.
#
felis_units = {'nanomaggies': 'nanomaggy',
               'nanomaggies^2': 'nanomaggy^2',
               'nanomaggies^{-2}': 'nanomaggy^-2',
               '1/nanomaggies^2': 'nanomaggy^-2',
               'nanomaggies/arcsec^2': 'nanomaggy arcsec^-2',
               '1e-17 erg/s/cm^2/AA': '1e-17 erg s-1 cm-2 Angstrom-1',
               '10<sup>-17</sup> ergs/cm<sup>2</sup>/s/A': '1e-17 erg s-1 cm-2 Angstrom-1',
               '1e-17 erg/s/cm^2': '1e-17 erg s-1 cm-2',
               '10<sup>-17</sup> ergs/cm<sup>2</sup>/s': '1e-17 erg s-1 cm-2',
               'ergs/cm2/s': 'erg s-1 cm-2',
               'erg/cm2/s': 'erg s-1 cm-2',
               'W/m2/Hz': 'W m-2 Hz-1',
               'log(counts/s)': 'log(count/s)',
               'sec': 's',
               'days': 'd',
               'years': 'yr',
               'Gyrs': 'Gyr',
               'Angstroms': 'Angstrom',
               'Ang': 'Angstrom',
               'microns': 'um',
               'degrees': 'deg'}


def _options():
    """Parse command-line options.
    """
    prsr = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
                                   description='Transform a TapSchema JSON file to felis/YAML.')
    prsr.add_argument('-o', '--output', metavar='FILE',
                      help=("Write output to FILE. By default, output is written to " +
                            "the same directory as the input file with .json changed to .yaml."))
    prsr.add_argument('-V', '--skip-validate', action='store_false', dest='validate',
                      help='If set, do not perform felis validation on the output.')
    prsr.add_argument('json', metavar='JSON', help='Name of a JSON file to convert.')
    return prsr.parse_args()


def main():
    """Entry-point for command-line scripts.

    Returns
    -------
    :class:`int`
        An integer suitable for passing to :func:`sys.exit()`.
    """
    options = _options()
    schema_name = os.path.splitext(options.json)
    schema_basename = os.path.basename(schema_name[0])
    assert schema_name[1] == '.json'
    with open(options.json) as j:
        json_schema = json.load(j)
    assert len(json_schema['schemas']) == 1
    assert json_schema['schemas'][0]['schema_name'] == schema_basename

    felis_schema = {'name': json_schema['schemas'][0]['schema_name'],
                    '@id': '#' + json_schema['schemas'][0]['schema_name'],
                    'description': json_schema['schemas'][0]['description'],
                    'version': {'current': 'v1',
                                'compatible': ['v1'],
                                'read_compatible': ['v1'],},
                    'tables':list()}

    for tap_index, json_table in enumerate(json_schema['tables']):
        assert json_table['schema_name'] == schema_basename
        felis_table = {'name': json_table['table_name'],
                       '@id': f"#{schema_basename}.{json_table['table_name']}",
                       'description': json_table['description'],
                       'tap:table_index': tap_index + 1,
                       'primaryKey': '',
                       'indexes': list(),
                       'columns': list()}
        json_columns = [c for c in json_schema['columns']
                        if (c['table_name'] == json_table['table_name'])
                        or (c['table_name'] == f"{schema_basename}.{json_table['table_name']}")]

        for column_index, json_column in enumerate(json_columns):
            #
            # TODO: Are TAP indexes 0-based or 1-based?
            #
            try:
                felis_datatype = felis_datatypes[json_column['datatype']]
            except KeyError:
                felis_datatype = json_column['datatype']
            felis_column = {'name': json_column['column_name'],
                            '@id': f"#{schema_basename}.{json_table['table_name']}.{json_column['column_name']}",
                            'description': json_column['description'],
                            'datatype': felis_datatype,
                            'nullable': False,
                            # 'fits:tunit': json_column['unit'],
                            # 'ivoa:ucd': json_column['ucd'],
                            # 'votable:utype': json_column['utype'],
                            # 'votable:arraysize': json_column['size'],
                            'tap:principal': json_column['principal'],
                            'tap:std': json_column['std'],
                            'tap:column_index': column_index + 1}
            if felis_datatype == 'string':
                felis_column['length'] = json_column['size']
            if json_column['indexed']:
                felis_index = {'name': f"{json_table['table_name']}_{json_column['column_name']}_idx",
                               '@id': f"#{json_table['table_name']}_{json_column['column_name']}_idx",
                               'columns': [felis_column['@id']]}
                felis_table['indexes'].append(felis_index)
            if json_column['unit']:
                if json_column['unit'] in felis_units:
                    felis_column['fits:tunit'] = felis_units[json_column['unit']]
                else:
                    felis_column['fits:tunit'] = json_column['unit']
            if json_column['ucd']:
                felis_column['ivoa:ucd'] = json_column['ucd']
            felis_table['columns'].append(felis_column)

        felis_schema['tables'].append(felis_table)

    if options.output is None:
        felis_yaml = schema_name[0] + '.yaml'
    else:
        felis_yaml = options.output

    with open(felis_yaml, 'w') as y:
        y.write('---\n')
        yaml.dump(felis_schema, y)

    if options.validate:
        proc = subprocess.Popen(['felis', 'validate', felis_yaml],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        status = proc.returncode
        out = out.decode('utf-8')
        err = err.decode('utf-8')
        err == f"INFO:felis:Validating {felis_yaml}"
        if status != 0 or err != f"INFO:felis:Validating {felis_yaml}\n":
            if out:
                print('STDOUT =')
                print(out)
            print('STDERR =')
            print(err)
    else:
        status = 0

    return status


if __name__ == '__main__':
    sys.exit(main())


