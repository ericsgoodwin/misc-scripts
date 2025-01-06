import arcpy
import pandas as pd


def get_bbox(fc, feature_index=None):
    """
    Get the bounding box in a comma-delineated format of a polygon feature class, or a feature in a polygon fc.

    Args:
        fc: Polygon feature class
        feature_index: the index value of the polygon fc. Used for looping through the fc.

    Returns: List of values [minx, miny, maxx, maxy]

    """
    with arcpy.da.SearchCursor(fc, ["SHAPE@"]) as cursor:
        for i, row in enumerate(cursor):
            if feature_index:
                if i == feature_index:
                    extent = row[0].extent
                    minx, maxx, miny, maxy = extent.XMin, extent.XMax, extent.YMin, extent.YMax
                    return [minx, miny, maxx, maxy]


def table_to_data_frame(in_table, input_fields=None, where_clause=None):
    """Function will convert an arcgis table into a pandas dataframe with an object ID index, and the selected
    input fields using an arcpy.da.SearchCursor.

    Parameters:
        in_table (str): The path to a non-spatial table in a .gdb
        input_fields (list): List of input fields within "in_table" to convert to DataFrame. Default is all fields.
        where_clause (str): SQL query to convert rows only matching the query

    Outputs:

    """
    OIDFieldName = arcpy.Describe(in_table).OIDFieldName
    if input_fields:
        final_fields = [OIDFieldName] + input_fields
    else:
        final_fields = [field.name for field in arcpy.ListFields(in_table)]
    data = [row for row in arcpy.da.SearchCursor(in_table, final_fields, where_clause=where_clause)]
    fc_dataframe = pd.DataFrame(data, columns=final_fields)
    fc_dataframe = fc_dataframe.set_index(OIDFieldName, drop=True)
    return fc_dataframe

