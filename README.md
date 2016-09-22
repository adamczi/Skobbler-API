# Catchment Area

This is a QGIS plugin that returns catchment feature in a shapefile based on user input. Plugin can use Skobbler's RealReach™ service or HERE's Isoline. These show how far can you get by car, bike or walk within desired minutes or meters. The result is returned as a memory layer.

The plugin uses geocoding service provided by [Nominatim](http://wiki.openstreetmap.org/wiki/Nominatim).

API keys must be provided by user in order to use this plugin. Input them in the *Settings* tab and they will be saved in your local QGIS settings.


#### Instructions:

- Click on the map, select your preferences, click *OK* and you will get desired catchment from the location you clicked

    or

- Select features of a point layer, set preferences and click *OK* and you will get a multipolygon containing as many catchments as features you selected. *Note - the layer you chose must be an "active" layer, meaning it has to be selected in QGIS Layers menu*


Selection has a priority over mouse click, so if both are satisfied, the selection method will be performed. If there are selcted features but your other layer is active, catchment will be prepared for location from mouse click if there was any.


More information - see: 

- [developer.skobbler.com](http://developer.skobbler.com/)

- [developer.here.com](https://developer.here.com/rest-apis/documentation/routing/topics/request-isoline.html)