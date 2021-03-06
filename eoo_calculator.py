#-----------------------------------------

# EOO_Calculator_v1.2.py
# Version:1.2
# Adrian Hughes IUCN
# 13th August 2014
# Useage: This script will only work with ArcGIS 10.1 or above advanced version. The convenx hull method of the ESRI minimum bounding geometry tool requires the advanced version
# Version notes: Bug fixes: last version  needed input data to have seasonal field even if IUCN attributes were not ticked.
#                This version automatically calculates a non breeding EOO if species has a non-breeding range
#                and also caluclates default EOO using P1-2, O1-2, S1-2 previous version included S3
# The script calculates EOO by creating a convex hull minimum bounding geometry for each species range with the specified hardcoded mapping codes (see below)
# The data is then projected to the cylindrical equal area projected coordinate system and the area of the EOO is
# calculated in km2 and added to the attribute data of the output for each species
# EOO is calculated around polygons or points with attribute values satisfying P1-2, O1-2, S1-2
# If user unchecks 'use IUCN attributes' checkbox then attribute values are ignored and EOO is calculated from all input data
# Warning: Tool can sometimes crash ArcMap if large complex geometries are used


import IUCNSP
import shutil
import sys
import os
import traceback
import inspect
import arcpy
from arcpy import env
import datetime

try:          
        
    

    # Parameters    
    Input = arcpy.GetParameterAsText(0)
    speciesfield = arcpy.GetParameterAsText(1)
    workspace = arcpy.GetParameter(2)
    use_attributes = arcpy.GetParameterAsText(3)

    # Variables
    S3count = 0
  

    # Setting workspace and get default spatial ref file on disk
    arcpy.env.workspace = workspace
    srfile  = os.path.dirname(Input)

    
    # get a unique list of values/species names and sort    
    specieslist = IUCNSP.GetUniqueValuesFromShapefile(Input, speciesfield)
    specieslist.sort()

    

    # set up proj for calculate areas, getting the proj file from tooldata folder
    spatialref = arcpy.CreateObject("SpatialReference")

    scriptpath = sys.argv[0]
    pathlist = os.path.dirname(scriptpath).split(os.sep)[:-1]
    path = ''    
    for eachitem in pathlist:
        path += eachitem + os.sep   
    
    CEApath = path + os.sep + 'tooldata' + os.sep + r"Cylindrical Equal Area (world).prj"
    WGS84path = path + os.sep + 'tooldata' + os.sep + r"WGS 1984.prj"   
    
       

    # Check if inputlist is null
    if not specieslist:
        IUCNSP.Printboth('No binomial found, exiting program.')
        sys.exit(2)
        
    
        
        
    for species in specieslist:      
        IUCNSP.Printboth("Processing " + species)
        species_valid = IUCNSP.CleanSpeciesName(species)      
        feature_eoo =  species_valid + "_EOO"
        feature_eoo_proj =  species_valid + "_EOO_proj"
        feature_eoo_nb_proj = species_valid + "_EOO_NB_proj"


         # search for non-breeding data (Seasonal = 3)
        if str(use_attributes) == 'true':
                   
            defwhereclause =  speciesfield + " = '" + species + "' AND  \"SEASONAL\" = 3"        
            arcpy.MakeFeatureLayer_management(Input, "nblyr", defwhereclause)
            result = arcpy.GetCount_management("nblyr")
            S3count= int(result.getOutput(0))           

        
       # set default where clause
        if str(use_attributes) == 'true':
            IUCNSP.Printboth("using IUCN attributes")
            defwhereclause =  speciesfield + " = '" + species + "' AND \"PRESENCE\"  In (1,2) AND \"ORIGIN\" In (1,2) AND \"SEASONAL\" In (1,2)"
        else:
            defwhereclause =  speciesfield + " = '" + species + "'"
            
        arcpy.MakeFeatureLayer_management(Input, "lyr", defwhereclause)       
                    

        # Calculate min bounding geometry
        IUCNSP.Printboth("...calculating min bounding geometry")
        arcpy.MinimumBoundingGeometry_management("lyr",feature_eoo,"CONVEX_HULL", "ALL")

        # Project to cylindrical equal area to calculate area
        IUCNSP.Printboth("...projecting and calculating area")
        arcpy.Project_management(feature_eoo,feature_eoo_proj, CEApath)


        # Add field to store binomial and area in sqkm
        IUCNSP.AddFieldWithValue(feature_eoo_proj, "BINOMIAL", "TEXT", "'" + species + "'")
        IUCNSP.AddField(feature_eoo_proj, "EOO_AREA_SQKM", "FLOAT")        
        arcpy.CalculateField_management(feature_eoo_proj, "EOO_AREA_SQKM",'!SHAPE_Area! / 1000000', "PYTHON")
        arcpy.Delete_management(feature_eoo)


       


        # calculate EOO for non-breeding range if S3 data exists and user checked use IUCN attributes box
        if S3count > 0 and  str(use_attributes) == 'true':

            IUCNSP.Printboth("Non-breeding data exists for this species. Calculating Non Breeding EOO...")
            defwhereclause =  speciesfield + " = '" + species + "' AND \"PRESENCE\"  In (1,2) AND \"ORIGIN\" In (1,2) AND \"SEASONAL\" In (1,3)"
            arcpy.MakeFeatureLayer_management(Input, "nblyr", defwhereclause)

            # Calculate min bounding geometry
            IUCNSP.Printboth("...calculating min bounding geometry")
            arcpy.MinimumBoundingGeometry_management("nblyr",feature_eoo,"CONVEX_HULL", "ALL")

            # Project to cylindrical equal area to calculate area
            IUCNSP.Printboth("...projecting and calculating area")
            arcpy.Project_management(feature_eoo,feature_eoo_nb_proj, CEApath)


            # Add field to store binomial and area in sqkm
            IUCNSP.AddFieldWithValue(feature_eoo_nb_proj, "BINOMIAL", "TEXT", "'" + species + "'")
            IUCNSP.AddField(feature_eoo_nb_proj, "EOO_NB_SQKM", "FLOAT")        
            arcpy.CalculateField_management(feature_eoo_nb_proj, "EOO_NB_SQKM",'!SHAPE_Area! / 1000000', "PYTHON")
            #arcpy.Delete_management(feature_eoo)  
                
        
        

   
    IUCNSP.Printboth("Species %s has finished"%str(species))
    
except arcpy.ExecuteError: 
    # Get the tool error messages 
    # 
    msgs = arcpy.GetMessages(2) 

    # Return tool error messages for use with a script tool 
    #
    arcpy.AddError(msgs) 

    # Print tool error messages for use in Python/PythonWin 
    # 
    print msgs

except:
    # Get the traceback object
    #
    tb = sys.exc_info()[2]
    tbinfo = traceback.format_tb(tb)[0]

    # Concatenate information together concerning the error into a message string
    #
    pymsg = "PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n" + str(sys.exc_info()[1])
    msgs = "ArcPy ERRORS:\n" + arcpy.GetMessages(2) + "\n"

    # Return python error messages for use in script tool or Python Window
    #
    arcpy.AddError(pymsg)
    arcpy.AddError(msgs)

    # Print Python error messages for use in Python / Python Window
    #
    print pymsg + "\n"
    print msgs


    
