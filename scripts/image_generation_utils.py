import typing
from functools import lru_cache
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import requests

# ISO3166 source list
# see https://github.com/lukes//ISO-3166-Countries-with-Regional-Codes

ISO3_URL = "https://raw.githubusercontent.com/lukes/ISO-3166-Countries-with-Regional-Codes/master/all/all.csv"


@lru_cache(maxsize=None)
def get_iso3_codes() -> typing.TypedDict:
    iso3_df = pd.read_csv(ISO3_URL)
    iso3_lookup = {item["name"].lower(): item for item in iso3_df.to_dict("records")}
    return iso3_lookup


def get_iso3_code(region: str, code: str = "alpha-3") -> typing.Optional[str]:
    """
    Returns the country ISO-3166 code
    Args:
        region (str): Common short country name. Refer to https://data.worldbank.org/country for possible values
        code (str): The country code standard, either 'alpha-3' or 'alpha-2'
    """
    # TODO: Find more elegant solution to correct country common name to ISO standard spelling
    iso_standard_region_name_lookup = {
        "vietnam": "viet nam",
        "laos": "lao people's democratic republic",
        "lao pdr": "lao people's democratic republic",
        "east-timor": "timor-leste",
    }
    iso3_lookup = get_iso3_codes()
    iso3_entry = iso3_lookup.get(iso_standard_region_name_lookup.get(region, region))
    return iso3_entry.get(code, None) if iso3_entry is not None else None


GEOBOUNDARIES_REQUEST_URL = "https://www.geoboundaries.org/gbRequest.html?ISO={}&ADM={}"


@lru_cache(maxsize=None)
def get_geoboundaries_url(region: str, adm: str = "ADM0") -> typing.Optional[str]:
    """
    Returns the download URL for the GeoBoundaries of a specified region and administrative level.

    Args:
        region (str): Name of the region for which to retrieve the geo boundaries.
        adm (str, optional): Administrative level of the boundaries to retrieve. Defaults to 'ADM0'.

    Returns:
        str: The download URL for the GeoBoundaries of the specified region and administrative level.
             Returns None if the region cannot be found or no boundary information is available.
    """

    iso = get_iso3_code(region)
    if iso is None:
        return None
    adm = adm.upper()
    url = GEOBOUNDARIES_REQUEST_URL.format(iso, adm)
    r = requests.get(url)
    respjson = r.json()
    if respjson is None or len(respjson) < 1 or "gjDownloadURL" not in respjson[0]:
        # raise ValueError(f'Invalid results returned from reqest {url} : response is {respjson}')
        return None
    dl_path = respjson[0]["gjDownloadURL"]
    return dl_path


@lru_cache(maxsize=None)
def get_admin_gdf(region: str, adm: str = "ADM0") -> typing.Optional[gpd.GeoDataFrame]:
    """
    Fetches administrative boundaries of a specified region and returns a GeoDataFrame object.

    Args:
        region (str): The name of the region to fetch boundaries for.
        adm (str, optional): The administrative level of the region's boundaries to fetch. Defaults to 'ADM0',
            which corresponds to country-level boundaries.

    Returns:
        GeoDataFrame: A GeoDataFrame object containing the administrative boundaries of the specified region.

    Example:
        >>> get_admin_gdf('timor-leste', 'ADM1')
    """

    admin_url = get_geoboundaries_url(region, adm=adm)
    if admin_url is None:
        return None
    admin_gdf = gpd.read_file(admin_url)
    if admin_gdf is None:
        return None
    admin_gdf = admin_gdf.to_crs("EPSG:4326")
    return admin_gdf


@lru_cache(maxsize=None)
def get_gdf_data(url: str) -> typing.Optional[gpd.GeoDataFrame]:
    """
    Downloads and returns GeoDataFrame data from a specified URL.

    Args:
        url (str): The URL of the data to be downloaded.

    Returns:
        GeoDataFrame: A GeoDataFrame object containing the downloaded data.

    Example:
        >>> get_gdf_data('https://example.com/data.gpkg')
    """
    gdf = gpd.read_file(url)
    if gdf is None:
        return None
    gdf = gdf.to_crs("EPSG:4326")
    return gdf


def make_image(
    id: str,
    admin_gdf: gpd.GeoDataFrame,
    data_gdf: gpd.GeoDataFrame,
    size: tuple = (17, 12),
    admin_color: str = "b",
    data_color: str = "r",
    output_dir: Path = Path(""),
) -> None:
    """
    Creates a map image from GeoDataFrame data and saves it to disk.

    Args:
        id (str): The identifier for the output image file.
        admin_gdf (GeoDataFrame): A GeoDataFrame object containing administrative boundary data to display.
        data_gdf (GeoDataFrame): A GeoDataFrame object containing data to overlay on the administrative boundaries.
        size (tuple, optional): The size of the output image in inches. Defaults to (17, 12).
        admin_color (str, optional): The color to use for the administrative boundaries. Defaults to 'b'.
        data_color (str, optional): The color to use for the overlay data. Defaults to 'r'.
        output_dir (Path, optional): The directory where the output image file should be saved. Defaults to the current directory.

    Returns:
        None

    Example:
        >>> make_image('map1', admin_gdf, data_gdf, output_dir=Path('/path/to/images'))
    """

    fig, ax = plt.subplots()
    if admin_gdf is not None:
        ax = admin_gdf.plot(ax=ax, facecolor="none", edgecolor=admin_color, alpha=0.85)
        crs = admin_gdf.crs
    if data_gdf is not None:
        ax = data_gdf.plot(ax=ax, facecolor="none", edgecolor=data_color, alpha=0.25)
        crs = data_gdf.crs
    plt.tick_params(
        axis="both",
        which="both",
        bottom=False,
        top=False,
        left=False,
        right=False,
        labelbottom=False,
        labelleft=False,
    )
    cx.add_basemap(ax, crs=crs.to_string())
    fig.set_size_inches(*size)
    plt.savefig(f"{output_dir}/{id}.png", pad_inches=0.0, bbox_inches="tight", dpi=100)


def first(items: typing.List[typing.Any]) -> typing.Optional[typing.Any]:
    """
    Gets the first item from a list or None if the list is empty
    """
    try:
        return next(iter(items))
    except StopIteration:
        return None


def generate_catalog_item_image(
    item: typing.TypedDict,
    image_args: typing.TypedDict = dict(size=(17, 12), admin_color="b", data_color="r"),
    output_dir: Path = Path(""),
) -> int:
    """
    Generates an image for a catalog item and saves it to disk.

    Args:
        item (TypedDict): A dictionary containing metadata for the catalog item to generate an image for.
        image_args (TypedDict, optional): A dictionary containing arguments to pass to the make_image() function.
            Defaults to {'size': (17,12), 'admin_color': 'b', 'data_color': 'r'}.
        output_dir (Path, optional): The directory where the output image file should be saved. Defaults to the current directory.

    Returns:
        int: An exit code indicating the status of the function. Returns 0 if successful and 1 if an error occurred.

    Example:
        >>> image_args = {'size': (10, 10), 'admin_color': 'r', 'data_color': 'g'}
        >>> generate_catalog_item_image(item, image_args, Path('/path/to/images'))
    """
    data_url = first(
        [link["url"] for link in item["links"] if "geojson" in link["type"]]
    )
    region = item.get("country-region", None)
    id = item["id"]
    if region is None and data_url is None:
        print(
            f"Warning: The catalog file {id}.yml didn't  find a valid region and geojson url to generate an image from"
        )
        return 1
    data_gdf = None
    if data_url:
        data_gdf = get_gdf_data(data_url)
    admin_gdf = None
    if region:
        admin_gdf = get_admin_gdf(region)
    if data_gdf is None and admin_gdf is None:
        print(
            f"Warning: The catalog file {id}.yml did't find a valid admin boundaries file and geojson dataset to generate an image from"
        )
        return 1
    make_image(item["id"], admin_gdf, data_gdf, output_dir=output_dir, **image_args)
    return 0