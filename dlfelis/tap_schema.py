#!/usr/bin/env python
# Licensed under a BSD-style 3-clause license - see LICENSE.md.
# -*- coding: utf-8 -*-
"""
dlfelis.tap_schema
==================

Tools for working with Astro Data Lab's TapSchema_.

.. _TapSchema: https://github.com/astro-datalab/TapSchema
"""
import argparse
import json
import logging
import os
import subprocess
import sys
import yaml
from astropy import units as u

#
# Conversion between types used in TapSchema and types required by Felis.
#
felis_datatypes = {'bigint': 'long',
                   'BIGINT': 'long',
                   'integer': 'int',
                   'INTEGER': 'int',
                   'smallint': 'short',
                   'SMALLINT': 'short',
                   'real': 'float',
                   'REAL': 'float',
                   'character': 'char',
                   'CHAR': 'char',
                   'varchar': 'string',
                   'DOUBLE': 'double',
                   'adql:INTEGER': 'int',
                   'adql:integer': 'int',
                   'adql:SMALLINT': 'short',
                   'adql:smallint': 'short',
                   'adql:SMALLINT[]': 'short',
                   'adql:BIGINT': 'long',
                   'adql:bigint': 'long',
                   'adql:REAL': 'float',
                   'adql:real': 'float',
                   'adql:REAL[]': 'float',
                   'adql:DOUBLE': 'double',
                   'adql:double': 'double',
                   'adql:DOUBLE[]': 'double',
                   'adql:CHAR': 'char',
                   'adql:char': 'char',
                   'adql:character': 'char',
                   'adql:character(1)': 'char',
                   'adql:VARCHAR': 'string',
                   'adql:varchar': 'string',
                   'adql:VARCHAR(n)': 'string',
                   'adql:TIMESTAMP': 'timestamp',
                   'adql:POINT': 'point',
                   'adql:REGION': 'region',
                   'adql:BOOLEAN': 'boolean',
                   'adql:text': 'string'
                   }
#
# Conversion between units used in TapSchema and units recommended by Felis,
# which adheres to the FITS standard.
#
felis_units = {'nanomaggies': 'nanomaggy',
               'Mgy': 'mgy',
               'nanomaggies^2': 'nanomaggy^2',
               'nanomaggies^{-2}': 'nanomaggy^-2',
               '1/nanomaggies^2': 'nanomaggy^-2',
               'nanomaggies/arcsec^2': 'nanomaggy arcsec^-2',
               '1e-17 erg/s/cm^2/AA': '1e-17 erg s-1 cm-2 Angstrom-1',
               '10<sup>-17</sup> ergs/cm<sup>2</sup>/s/A': '1e-17 erg s-1 cm-2 Angstrom-1',
               'erg/cm2/s/A': 'erg cm-2 s-1 Angstrom-1',
               'erg/s/A': 'erg s-1 Angstrom-1',
               'erg/cm2/s/A/A': 'erg cm-2 s-1 Angstrom-2',
               '1e-17 erg/s/cm^2': '1e-17 erg s-1 cm-2',
               '10<sup>-17</sup> ergs/cm<sup>2</sup>/s': '1e-17 erg s-1 cm-2',
               'ergs/cm2/s': 'erg s-1 cm-2',
               'erg/cm2/s': 'erg s-1 cm-2',
               'W/m2/Hz': 'W m-2 Hz-1',
               'log(counts/s)': 'dex(count/s)',
               'Counts': 'count',
               'Electrons': 'electron',
               'sec': 's',
               'seconds': 's',
               'Seconds': 's',
               'days': 'd',
               'Days': 'd',
               'years': 'yr',
               'Julian years': 'yr',
               'Gyrs': 'Gyr',
               'Arcsec': 'arcsec',
               'Arcseconds': 'arcsec',
               'Arcseconds^2': 'arcsec^2',
               'Milliarcseconds/year': 'milliarcsecond/yr',
               'Angstroms': 'Angstrom',
               'Ang': 'Angstrom',
               'microns': 'um',
               'degrees': 'deg',
               'Degrees': 'deg',
               '1/Degrees': '1/deg',
               'ADU': 'adu',
               'pixels': 'pixel',
               'Pixels': 'pixel',
               'celsius': 'Celsius',
               'micro-Janskys': 'uJy',
               'magnitudes': 'mag',
               'mags': 'mag',
               'Magnitude': 'mag',
               'Magnitudes': 'mag',
               'Mag': 'mag',
               'AB mags': 'AB mag',
               '[mag x arcsec^{-2}]': 'mag/arcsec^2',
               'mag./sq.arcsec': 'mag/arcsec^2',
               'None': '',
               'Dimensionless': '',
               'Frequency[1/day]': '1/day',
               'e-/s': 'electron/s',
               'Electrons/ADU': 'electron/adu',
               'Time[Barycentric JD in TCB - 2455197.5 (day)]': 'd',
               'Angle[mas^-2]': 'mas^-2',
               'log(cm.s**-2)': 'dex(cm/s2)',
               '[10-7W]': '10-7W',
               '[cW/m2/nm]': 'cW m-2 nm-1',
               '[cw/m2/nm]': 'cW m-2 nm-1',
               'kilobytes': 'kilobyte',
               '1/(mas/yr)^2': 'mas2 yr-2',
               '1/(mas/year)^2': 'mas2 yr-2',
               '1/(mas)^2': 'mas^-2',
               'm_sun': 'M_sun',
               'l_sun': 'L_sun',
               'r_sun': 'R_sun',
               'Solar radius': 'R_sun',
               'r_sun/year': 'R_sun/yr',
               'm_sun/year': 'M_sun/yr',
               'kelvin': 'Kelvin',
               'log10(M_sun)': 'dex(M_sun)',
               'log Gyr<sup>-1</sup>': 'dex(Gyr^-1)',
               'log(count/s)': 'dex(count/s)',
               'log(cm^-2)': 'dex(cm^-2)',
               'Km/s': 'km/s',
               'ergs/s': 'erg/s',
               'solar masses per year': 'M_sun/yr',
               'log(M_solar)': 'dex(M_sun)',
               'dex (solar masses)': 'dex(M_sun)',
               'solar mass': 'M_sun',
               'solar metallicity': '',
               'E(B-V) mag': 'mag',
               '(3.63 nJy)^2': '13.1769 nJy^2',
               'sexigesimal hours': 'deg',  # in ivoa files
               'sexigesimal degrees': 'deg'  # in ivoa files
               }

#
# Conversion between UCDs used in some json files and UCDs required by felis/IVOA
#
felis_ucds = {'pos.gal.lon': 'pos.galactic.lon',
              'pos.gal.lat': 'pos.galactic.lat',
              'pos.ecl.lon': 'pos.ecliptic.lon',
              'pos.ecl.lat': 'pos.ecliptic.lat',
              'stat.ratio': 'stat.snr',
              'instr.filter': 'phys.transmission;instr.filter',
              'src.var;meta.number': 'meta.number;src.var',
              'phys.proper_motion': 'pos.pm',
              'phys.parallax': 'pos.parallax',
              'id_number': 'meta.record',
              'refer_code': 'meta.ref',
              'pos_eq_dec_off': 'pos.eq.dec;instr.offset',
              'pos_eq_ra_off': 'pos.eq.ra;instr.offset',
              'stat_prop': 'stat.probability',
              'pos_pos-ang': 'pos.posAng',
              'phys_ellipticity': 'src.ellipticity',
              'morph_param': 'src.morph.param',
              'error': 'stat.error',
              'phot_mag': 'phot.mag',
              'phot_color': 'phot.color',
              'pos_gal_lat': 'pos.galactic.lat',
              'pos_gal_lon': 'pos.galactic.lon',
              'pos_eq_x': 'pos.cartesian.x',
              'pos_eq_y': 'pos.cartesian.y',
              'pos_eq_z': 'pos.cartesian.z',
              'number': 'meta.number',
              'time_epoch': 'time.epoch',
              'fit_chi2': 'stat.fit.chi2',
              'pos_eq_pmra': 'pos.pm;pos.eq.ra',
              'pos_eq_pmdec': 'pos.pm;pos.eq.dec'
              }


def _options():
    """Parse command-line options.

    Returns
    -------
    :class:`~argparse.Namespace`
        Parsed command-line arguments.
    """
    prsr = argparse.ArgumentParser(prog=os.path.basename(sys.argv[0]),
                                   description='Transform a TapSchema JSON file to felis/YAML.')
    prsr.add_argument('-d', '--debug', action='store_true',
                      help='Debug mode, print extra information.')
    prsr.add_argument('-o', '--output', metavar='FILE',
                      help=("Write output to FILE. By default, output is written to " +
                            "the same directory as the input file with .json changed to .yaml."))
    prsr.add_argument('-V', '--skip-validate', action='store_false', dest='validate',
                      help='If set, do not perform felis validation on the output.')
    prsr.add_argument('json', metavar='JSON', help='Name of a JSON file to convert.')
    return prsr.parse_args()


def validate(filename):
    """Calls :command:`felis validate` on `filename`.

    Parameters
    ----------
    filename : :class:`str`
        Name of the file to validate.

    Returns
    -------
    :class:`int`
        Status returned by :command:`felis`.
    """
    log = logging.getLogger('dlfelis.tap_schema.validate')
    proc = subprocess.Popen(['felis', 'validate', filename],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    out = out.decode('utf-8')
    err = err.decode('utf-8')
    if proc.returncode != 0 or err != f"INFO:felis:Validating {filename}\n":
        if out:
            log.error('STDOUT =')
            log.error(out)
        log.error('STDERR =')
        log.error(err)
    return proc.returncode


def main():
    """Entry-point for command-line scripts.

    Returns
    -------
    :class:`int`
        An integer suitable for passing to :func:`sys.exit()`.
    """
    options = _options()
    log = logging.getLogger('dlfelis.tap_schema.main')
    if options.debug:
        log.setLevel(logging.DEBUG)
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
                                'read_compatible': ['v1'], },
                    'tables': list()}

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
                            '@id': (f"#{schema_basename}." +
                                    f"{json_table['table_name']}." +
                                    f"{json_column['column_name']}"),
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
            if felis_datatype in ['string', 'char']:
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
                if json_column['ucd'] in felis_ucds:
                    felis_column['ivoa:ucd'] = felis_ucds[json_column['ucd']]
                else:
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
        status = validate(felis_yaml)
    else:
        status = 0

    return status


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
