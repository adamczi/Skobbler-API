# -*- coding: utf-8 -*-
"""
/***************************************************************************
 skob
                                 A QGIS plugin
 This plugin uses Skobbler RealReach API
                              -------------------
        begin                : 2016-08-10
        git sha              : $Format:%H$
        copyright            : (C) 2016 by Adam Borczyk
        email                : ad.borczyk@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant, pyqtSignal, QObject, SIGNAL
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from skobbler_rr_dialog import skobDialog
import os.path
## Additional
from config import *
import urllib, urllib2, json
from qgis.core import QgsField, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPoint, QgsMapLayerRegistry, QgsCoordinateReferenceSystem, QgsCoordinateTransform
from qgis.gui import QgsMapTool, QgsMapCanvas, QgsMapToolEmitPoint, QgsMessageBar
import xml.etree.ElementTree as ET

class skob:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        ## Module to get points from mouse clicks
        self.canvas = self.iface.mapCanvas() 
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        self.cLayer = None
        ##

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'skob_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        ## Create the dialog (after translation) and keep reference. Window stays on top.
        self.dlg = skobDialog(self.iface.mainWindow())

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Skobbler API')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'skob')
        self.toolbar.setObjectName(u'skob')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('skob', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/skob/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Skobbler API'),
            callback=self.run,
            parent=self.iface.mainWindow())

        ## Trigger selectCoord on mouse click
        QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.selectCoord)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Skobbler API'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def checkBoxes(self):
        """ Disable Toll and Highway checkboxes if transportation other than 'car' """
        if self.dlg.radioButton_3.isChecked():
            self.dlg.checkBox_1.setEnabled(True)
            self.dlg.checkBox_2.setEnabled(True)
        else:
            self.dlg.checkBox_1.setEnabled(False)
            self.dlg.checkBox_2.setEnabled(False)
            self.dlg.checkBox_1.setCheckState(False)
            self.dlg.checkBox_2.setCheckState(False)            
        return

    def selectCoord(self, point):
        """ Gets coordinates from mouse click and reprojects it to 4326 if needed. Returns geocoded address"""
        ## Get mouse click coordinates
        self.pntGeom = QgsGeometry.fromPoint(point)
        self.selectedCoords = self.pntGeom.asPoint()
        
        ## Reproject if needed
        currentEPSG = self.canvas.mapRenderer().destinationCrs().authid()
        if currentEPSG != 'EPSG:4326':
            crsSrc = QgsCoordinateReferenceSystem(int(currentEPSG[5:]))    # WGS 84
            crsDest = QgsCoordinateReferenceSystem(4326)
            xform = QgsCoordinateTransform(crsSrc, crsDest)
            self.selectedCoords = xform.transform(self.pntGeom.asPoint())

        ## Get geocoded addres 
        latitude = self.selectedCoords.y()
        longitude = self.selectedCoords.x()
        nominatimString = separator.join((url_nominatim,
                                        lat
                                        + str(latitude),
                                        lon
                                        + str(longitude),
                                        details))
        ## Get and parse XML
        tree = ET.parse(urllib2.urlopen(nominatimString))
        root = tree.getroot()
        for node in root.findall('result'):
            adres = node.text
        else:
            for node in root.findall('error'):
                adres = node.text
        ## Write the address in the text box
        self.dlg.textBrowser.setPlainText(adres)

        return self.selectedCoords

    def createURL(self):
        """Construct the Skobbler API request"""
        ## Transportation type
        if self.dlg.radioButton_1.isChecked():
            transportation = 'pedestrian'
        elif self.dlg.radioButton_2.isChecked():
            transportation = 'bike'
        else:
            transportation = 'car'

        ## Tolls and highways if 'car'
        if self.dlg.checkBox_1.checkState():
            toll = 'toll=1'
        else: 
            toll = 'toll=0'
        if self.dlg.checkBox_2.checkState():
            highways = 'highways=1'
        else:
            highways = 'highways=0'

        ## Units
        if self.dlg.radioButton_4.isChecked():
            self.unit = 'meter'
            ## Distance value
            self.dist = self.dlg.spinBox.value()
        else:
            self.unit = 'sec'
            ## Distance value
            self.dist = self.dlg.spinBox.value()*60       

        startPoint = str(self.selectedCoords.y())+','+str(self.selectedCoords.x())

        ## Create URL
        self.urlWithParams = separator.join((url_skob
                                             + startPoint,
                                            transport
                                            + transportation,
                                            distance
                                            + str(self.dist),
                                            units
                                            + self.unit,
                                            toll,
                                            highways,
                                            nonReachable,
                                            response_type))

        self.createURLlist = (self.urlWithParams, self.dist, self.unit)
        return self.createURLlist

    def requestAPI(self):
        """ Send the request """
        queryString, dist, unit = self.createURL()
        ## Get the data
        response = urllib.urlopen(queryString)
        data = json.loads(response.read())
        try:
            self.coords = data['realReach']['gpsPoints']
        except KeyError:
            return 'keyerror'

    def createShapefile(self):
        """ Create shapefile from returned list of points """
        queryString, dist, unit = self.createURL() # to get params from URL
        name = "temp_"+str(dist)+'_'+unit
        vl = QgsVectorLayer("Polygon?crs=EPSG:4326", name, "memory")
        pr = vl.dataProvider()

        ## Add feature name in attribute table
            pr.addAttributes([QgsField("name", QVariant.String)])
            vl.updateFields()
        
        ## Create geometry from points
        points = []
        x = [self.coords[i] for i in range(1, len(self.coords), 2)]
        y = [self.coords[i] for i in range(0, len(self.coords), 2)]
        
        for i, j in zip(y[4:], x[4:]):
            points.append(QgsPoint(i,j))

        fet = QgsFeature()
        fet.setGeometry(QgsGeometry.fromPolygon([points]))

        ## Set feature name/attribute
        fet.setAttributes(["Reach"])
        pr.addFeatures([fet])

        vl.updateExtents()

        ## Add prepared layer with transparency
        QgsMapLayerRegistry.instance().addMapLayer(vl)
        vl.setLayerTransparency(50)

    def run(self):
        """Run method that performs all the real work"""
        self.dlg.textBrowser.clear()
        self.dlg.spinBox.setValue(10)

        ## Set clickTool as default method
        self.canvas.setMapTool(self.clickTool)

        self.dlg.checkBox_1.setEnabled(False)
        self.dlg.checkBox_2.setEnabled(False)

        self.dlg.radioButton_3.toggled.connect(self.checkBoxes)

        ## show the dialog
        self.dlg.show()

        ## Run the dialog event loop
        result = self.dlg.exec_()

        ## See if OK was pressed
        if result:
            if self.dlg.textBrowser.toPlainText() != '':

                self.createURL()
                
                if self.requestAPI() != 'keyerror':
                    self.createShapefile()
                else:
                    self.iface.messageBar().pushMessage("Error", "Invalid starting point - no roads around", level=QgsMessageBar.WARNING, duration=5)
            else:
                pass