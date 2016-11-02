# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import print_function
from astropy.extern.six import BytesIO
from astropy.table import Table
from astropy.io import fits
from ..query import BaseQuery
from ..utils import commons
from ..utils import async_to_sync
from . import conf

__all__ = ['Heasarc', 'HeasarcClass']

allowed_rad_units = ["degrees", "arcmin", "arcsec"]
common _parameter_description = "{PUT DESCIPTION HERE   }"


@async_to_sync
class HeasarcClass(BaseQuery):

    """HEASARC query class.
    """

    URL = conf.server
    TIMEOUT = conf.timeout

    def _base_query(self, table, object_name="", search_radius="Default", radius_unit="arcmin",
                    result_max=1000, display_mode='FitsDisplay',
                    get_query_payload=False, cache=True, **kwargs):
        """This is a base for the all querys to avoid duplation of
         code specific parameters are passed as keywords"""

        radius_unit = radius_unit.lower()
        if radius_unit in allowed_rad_units:
            raise ValueError("radius_unit is not {allowed}".format(", ".join(allowed_rad_units)))

        request_payload = kwargs
        request_payload["Entry"] = object_name
        request_payload["Radius"] = search_radius
        request_payload["Radius_unit"] = radius_unit
        request_payload["ResultMax"] = result_max
        request_payload['tablehead'] = ('BATCHRETRIEVALCATALOG_2.0 {}'
                                        .format(table))
        request_payload['Action'] = 'Query'
        request_payload['displaymode'] = display_mode

        if get_query_payload:
            return request_payload

        response = self._request('GET', self.URL, params=request_payload,
                                 timeout=self.TIMEOUT, cache=cache)
        return response

    def query_object_async(self, object_name, table, search_radius="Default",
                           radius_unit="arcmin", result_max=1000, cache=True,
                           get_query_payload=False, display_mode='FitsDisplay'):
        """TODO: document this!
        {common}
        """.format(common=common _parameter_description)
        return self._base_query(table, object_name=object_name, search_radius=search_radius, radius_unit=radius_unit,
                                result_max=result_max, display_mode=display_mode,
                                get_query_payload=get_query_payload, cache=cache)

    def query_id_async(self, obsid, table, op="=", cache=True,
                       get_query_payload=False,
                       display_mode='FitsDisplay'):
        """TODO: document this!
        {common}
        """.format(common=common _parameter_description)

        request_payload = dict()
        request_payload['Entry'] = ""
        request_payload['tablehead'] = 'name=heasarc_{table}'.format(table=table)
        request_payload['bparam_obsid'] = "{op}{obsid}".format(op=op, obsid=obsid)

        return self._base_query(table, search_radius=search_radius, radius_unit=radius_unit,
                                result_max=result_max, display_mode=display_mode,
                                get_query_payload=get_query_payload, cache=cache,
                                **request_payload)

    def _fallback(self, content):
        """
        Blank columns which have to be converted to float or in fail so
        lets fix that by replacing with -1's
        """

        data = BytesIO(content)
        header = fits.getheader(data, 1)  # Get header for column info
        colstart = [y for x, y in header.items() if "TBCOL" in x]
        collens = [int(float(y[1:]))
                   for x, y in header.items() if "TFORM" in x]
        new_table = []
        content = str(content, encoding="UTF-8")
        # stops strip from cleaning \n away which causes errors when line ends in spaces
        old_table = content.split("END")[-1].strip(" ")
        for line in [ln for ln in old_table.split("\n") if len(ln.strip()) > 0]:
            newline = []
            for n, tup in enumerate(zip(colstart, collens), start=1):
                cstart, clen = tup
                part = line[cstart - 1:cstart + clen]
                newline.append(part)
                if len(part.strip()) == 0:
                    if header["TFORM%i" % n][0] in ["F", "I"]:
                        # extra space is required to sperate column
                        newline[-1] = "-1".rjust(clen) + " "
            new_table.append("".join(newline))
        data = BytesIO(bytes(content.replace(old_table, "\n".join(new_table)), encoding="UTF-8"))
        return Table.read(data, hdu=1)

    def _parse_result(self, response, verbose=False):
        # if verbose is False then suppress any VOTable related warnings
        if not verbose:
            commons.suppress_vo_warnings()
        try:
            data = BytesIO(response.content)
            table = Table.read(data, hdu=1)
            return table
        except ValueError:
            return self._fallback(response.content)


Heasarc = HeasarcClass()
