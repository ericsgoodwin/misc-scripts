import arcpy
import arcpy.management
import pandas as pd
import math
import os


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

def scale_geom(geom, scale, reference=None):
    """
    Returns geom scaled to scale %
    Source: User Evil Genius via https://gis.stackexchange.com/questions/169694/polygon-resizing-in-arcpy-like-scale-tool-of-advanced-editing-toolbar-in-arcmap
    
    """
    if geom is None: return None
    if reference is None:
        # we'll use the centroid if no reference point is given
        reference = geom.centroid

    refgeom = arcpy.PointGeometry(reference)
    newparts = []
    for pind in range(geom.partCount):
        part = geom.getPart(pind)
        newpart = []
        for ptind in range(part.count):
            apnt = part.getObject(ptind)
            if apnt is None:
                # polygon boundaries and holes are all returned in the same part.
                # A null point separates each ring, so just pass it on to
                # preserve the holes.
                newpart.append(apnt)
                continue
            bdist = refgeom.distanceTo(apnt)

            bpnt = arcpy.Point(reference.X + bdist, reference.Y)
            adist = refgeom.distanceTo(bpnt)
            cdist = arcpy.PointGeometry(apnt).distanceTo(bpnt)

            # Law of Cosines, angle of C given lengths of a, b and c
            angle = math.acos((adist**2 + bdist**2 - cdist**2) / (2 * adist * bdist))

            scaledist = bdist * scale

            # If the point is below the reference point then our angle
            # is actually negative
            if apnt.Y < reference.Y: angle = angle * -1

            # Create a new point that is scaledist from the origin 
            # along the x axis. Rotate that point the same amount 
            # as the original then translate it to the reference point
            scalex = scaledist * math.cos(angle) + reference.X
            scaley = scaledist * math.sin(angle) + reference.Y

            newpart.append(arcpy.Point(scalex, scaley))
        newparts.append(newpart)

    return arcpy.Geometry(geom.type, arcpy.Array(newparts), geom.spatialReference)

def scale_fc(input_fc, output_fc, scale_factor):
    """
    Returns feature class with each feature scaled to scale %

    Args:
        input_fc: The path to the existing polygon feature class whose features will be scaled in a new/empty feature class.
        output_fc: The path to the not-yet-existent polygon feature class which will house the scaled polygons.
        scale_factor: A number between 0 and 1 which will be used to scale the features by %
    
    Returns:
        The output_fc polygon feature class (if a variable is set to be returned)
    """
    # Get the fields to include in the output
    fields = arcpy.ListFields(input_fc)
    field_names = [field.name for field in fields if field.type not in ("OID", "Geometry") and not field.required]

    out_gdb, out_name = os.path.split(output_fc)
    spatial_ref = arcpy.Describe(input_fc).spatialReference
        
    arcpy.management.CreateFeatureclass(out_path=out_gdb,
                                        out_name=out_name,
                                        geometry_type="POLYGON",
                                        spatial_reference=spatial_ref)


    # Add fields from input_fc to output_fc
    for field in fields:
        if field.name in field_names:
            arcpy.AddField_management(output_fc, field.name, field.type, 
                                        field.precision, field.scale, field.length)

    # Prepare field mapping for cursor use
    input_fields = ["SHAPE@"] + field_names
    output_fields = ["SHAPE@"] + field_names

    
    with arcpy.da.SearchCursor(input_fc, input_fields) as search_cursor, \
    arcpy.da.InsertCursor(output_fc, output_fields) as insert_cursor:
        for row in search_cursor:
            scaled_geom = scale_geom(row[0], scale_factor)
            insert_cursor.insertRow([scaled_geom] + list(row[1:]))
            

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

