# TerraClimate Soil Moisture Data for Cross-Country Validation
# Retrieved: July 7, 2026
# Source: Abatzoglou et al. (2018) Scientific Data
# Access: Free, no login, via THREDDS OPeNDAP
#   http://thredds.northwestknowledge.net:8080/thredds/ncss/grid/
#   agg_terraclimate_soil_1950_CurrentYear_GLOBE.nc
# Variable: soil (total column soil moisture, mm)
# Normalization: % of 2000-2025 maximum for each location
#
# Used in: Cross-country validation (Table 15)
# HardwareX_Smart_Flood_EWS.tex v1.0.0

# Climate normals (2000-2025)
# Station                    Min(mm)   Max(mm)   Mean(mm)
# 07374000 (Baton Rouge)      264      1958      1603
# 08068500 (Houston)          171      2442      1490
# 06934500 (Hermann, MO)      202      1609      1001

# Event data
# Mississippi 2011 (07374000 - Baton Rouge, LA)
# 2011-05-01:  637 mm = 33%   (flood peak, upstream-driven)
# 2011-06-01:  460 mm = 23%   (recession)

# Hurricane Harvey 2017 (08068500 - Spring Creek, Houston, TX)
# 2017-08-01: 2442 mm = 100%  (max, Harvey landfall)
# 2017-09-01: 1856 mm = 76%   (draining)

# Midwest 2019 (06934500 - Missouri River, Hermann, MO)
# 2019-03-01: 1609 mm = 100%  (spring flood peak)
# 2019-04-01: 1572 mm = 98%   (continued saturation)
# 2019-05-01: 1609 mm = 100%  (peak)
# 2019-06-01: 1553 mm = 97%   (still saturated)
# 2019-07-01: 1257 mm = 78%   (drying)
