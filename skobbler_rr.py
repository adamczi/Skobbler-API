# -*- coding: utf-8 -*-
"""
/***************************************************************************
 skob
                                 A QGIS plugin
 This plugin uses external APIs to create a shapefile with catchment area
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QVariant, pyqtSignal, QObject, Qt, SIGNAL, QSettings
from PyQt4.QtGui import QAction, QIcon, QToolBar, QCursor, QApplication
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from skobbler_rr_dialog import skobDialog
import os.path
## Additional
from utils import *
from epsg import *
import urllib2, json
from qgis.core import QgsField, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPoint, QgsMapLayerRegistry, QgsMapLayer
from qgis.gui import QgsMapTool, QgsMapCanvas, QgsMapToolEmitPoint, QgsMessageBar, QgsMapToolPan
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
        # self.cLayer = None
        

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
        self.menu = self.tr(u'&Location Intelligence')

        ## Add to LI tooblar or create if doesn't exist
        toolbarName = 'Location Intelligence'
        self.toolbar = self.iface.mainWindow().findChild(QToolBar,toolbarName)
        print self.toolbar
        if self.toolbar is None:
            self.toolbar = self.iface.addToolBar(toolbarName)
            self.toolbar.setObjectName(toolbarName)            

        self.dlg.spinBox.setValue(10)
        self.toggleProvider()
        self.readKeys()
        self.dlg.pushButton.clicked.connect(self.saveKeys)

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
            text=self.tr(u'Open Catchment Area'),
            callback=self.run,
            parent=self.iface.mainWindow())

        ## Trigger selectCoord on mouse click
        QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.selectCoord)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Catchment Area'),
                action)
            self.iface.removeToolBarIcon(action)
        
        ## remove the toolbar
        if len(self.toolbar.actions())==0:
            del self.toolbar

    def readKeys(self):
        """ Load API keys from global QGIS settings """
        s = QSettings()
        self.dlg.lineEdit.setText(s.value("catchment/skobbler_key"))
        self.dlg.lineEdit_2.setText(s.value("catchment/here_key"))

    def checkBoxes(self):
        """ Disable Toll and Highway checkboxes if transportation other than 'car' """
        if self.dlg.radioButton_3.isChecked() and self.dlg.radioButton.isChecked(): # Car + Skobbler
            self.dlg.checkBox_1.setEnabled(True)
            self.dlg.checkBox_2.setEnabled(True)
            self.dlg.checkBox_1.setText('Toll')
        elif self.dlg.radioButton_3.isChecked() and self.dlg.radioButton_6.isChecked(): # Car + Here
            self.dlg.checkBox_1.setEnabled(True)
            self.dlg.checkBox_1.setText('Traffic')
        else:
            self.dlg.checkBox_1.setEnabled(False)
            self.dlg.checkBox_2.setEnabled(False)
            self.dlg.checkBox_1.setCheckState(False)
            self.dlg.checkBox_2.setCheckState(False)            

    def selectCoord(self, point):
        """ Gets coordinates from mouse click and reprojects it to 4326 if needed. Returns geocoded address"""
        ## Get mouse click coordinates
        self.pntGeom = QgsGeometry.fromPoint(point)
        self.coordsClick = self.pntGeom.asPoint()
        
        ## Reproject if needed
        EPSG(self)

        ## Get geocoded addres 
        latitude = str(self.coordsClick.y())
        longitude = str(self.coordsClick.x())

        ## Get and parse XML
        tree = ET.parse(urllib2.urlopen(nominatimString % (latitude, longitude)))
        root = tree.getroot()
        for node in root.findall('result'):
            adres = node.text
        else:
            for node in root.findall('error'):
                adres = node.text
        ## Write the address in the text box
        self.dlg.textBrowser.setPlainText(adres)

        return self.coordsClick

    def coordsFromAttr(self):
        """ Get coordinates from attributes if any selected """ 
        features = []
        coordsTemp = []
        self.coordsFeatures = []
        layer = self.iface.activeLayer()

        try:
            if layer.wkbType() % 3 == 1: ## if Point layer
                features.append(layer.selectedFeatures())

                for f in range(len(features[0])):
                    if features[0][f].geometry().isMultipart():
                        feat = features[0][f].geometry().asMultiPoint()[0]
                    else:
                        feat = features[0][f].geometry().asPoint()

                    coordsTemp.append(str(feat.x())+','+str(feat.y()))
                    
                self.coordsFeatures = [map(float,i.split(',')) for i in coordsTemp]

                return self.coordsFeatures

        except AttributeError:
            pass

    def chooseCoords(self):
        """ Choose between coordinates from mouse click or from selected features """
        selectedCoords = []
        if self.coordsFromAttr() == [] or self.coordsFromAttr() is None: # from mouse click if no feature selected
            selectedCoords.append(self.coordsClick)
            self.createShapefile(selectedCoords)
        else: # if from selected features
            for i in range(len(self.coordsFeatures)):
                selectedCoords.append(QgsPoint(self.coordsFeatures[i][0],self.coordsFeatures[i][1]))
            self.createShapefile(selectedCoords)

    def toggleProvider(self):
        """ Adjust possible route options to both providers if one or other selected """
        if self.dlg.radioButton.isChecked(): # if Skobbler
            self.dlg.checkBox_1.setText('Toll') # Traffic to Toll
            self.dlg.lineEdit.setDisabled(False) # S key
            self.dlg.lineEdit_2.setDisabled(True) # H key
            # self.dlg.checkBox_1.setEnabled(True) # Toll
            self.dlg.checkBox_2.setEnabled(True) # Highway
            self.dlg.radioButton_1.setEnabled(True) # Walk
            self.dlg.radioButton_2.setEnabled(True) # Bike
        else: # if HERE
            self.dlg.lineEdit.setDisabled(True) # S key
            self.dlg.lineEdit_2.setDisabled(False) # H key
            if self.dlg.radioButton_3.isChecked(): # Traffic
                self.dlg.checkBox_1.setEnabled(True)
            else:
                self.dlg.checkBox_1.setEnabled(False) 
            self.dlg.checkBox_1.setText('Traffic') # Toll to traffic
            self.dlg.checkBox_2.setEnabled(False) # Highway
            # self.dlg.checkBox_1.setCheckState(False) # Toll
            self.dlg.checkBox_2.setCheckState(False) # Highway
            self.dlg.radioButton_1.setEnabled(False) # Walk
            self.dlg.radioButton_2.setEnabled(False) # Bike

            if self.dlg.radioButton_1.isChecked() or self.dlg.radioButton_2.isChecked(): # Walk or Bike in HERE
                self.dlg.radioButton_3.setChecked(True) # Car

    def createSkobblerURL(self, selectedCoords):
        """Construct the Skobbler API request"""
        ## Transportation type
        if self.dlg.radioButton_1.isChecked():
            self.transportation = 'pedestrian'
        elif self.dlg.radioButton_2.isChecked():
            self.transportation = 'bike'
        else:
            self.transportation = 'car'

        ## Tolls, highways,  if 'car' and units + distance
        toll = 'toll=1' if self.dlg.checkBox_1.checkState() else 'toll=0'
        highways = 'highways=1' if self.dlg.checkBox_2.checkState() else 'highways=0'
        self.unit = 'meter' if self.dlg.radioButton_4.isChecked() else 'sec'
        self.dist = self.dlg.spinBox.value() if self.dlg.radioButton_4.isChecked() else self.dlg.spinBox.value()*60

        ## Starting point from mouse click
        startPoint = str(selectedCoords.y())+','+str(selectedCoords.x())

        ## Create URL
        self.createURLlist = (urlSkobParams % (startPoint, self.transportation, str(self.dist), self.unit, toll, highways),
                             self.dist, self.unit)

        return self.createURLlist

    def createHereURL(self, selectedCoords):
        """Construct the HERE API request"""
        ## Transportation type
        if self.dlg.radioButton_2.isChecked():
            self.transportation = 'bicycle'
        else:
            self.transportation = 'car'

        ## Traffic  if 'car' and units + distance
        traffic = 'enabled' if self.dlg.checkBox_1.checkState() else 'disabled'
        self.unit = 'distance' if self.dlg.radioButton_4.isChecked() else 'time'
        self.dist = self.dlg.spinBox.value() if self.dlg.radioButton_4.isChecked() else self.dlg.spinBox.value()*60

        ## Starting point from mouse click
        startPoint = str(selectedCoords.y())+','+str(selectedCoords.x())

        ## Create URL
        self.createURLlist = (urlHereParams % (self.transportation, traffic, startPoint, self.dist, self.unit), 
                            self.dist, self.unit)

        return self.createURLlist

    def requestAPI(self, selectedCoords):
        """ Send the request """
        queryString, dist, unit = self.createSkobblerURL(selectedCoords) if self.dlg.radioButton.isChecked() else self.createHereURL(selectedCoords)

        ## Get the data
        try:
            response = urllib2.urlopen(queryString)
            data = json.loads(response.read())
            if self.dlg.radioButton.isChecked(): # Skobbler
                self.coordsResponse = data['realReach']['gpsPoints']
            else: # HERE
                self.coordsResponse = data['response']['isoline'][0]['component'][0]['shape']
        except KeyError, urllib2.HTTPError:
            return 'keyerror'

    def createShapefile(self, selectedCoords):
        """ Create shapefile from returned list of points """
        ## Basic parameters - name, type, epsg
        name = "temp_catchment"
        vl = QgsVectorLayer("Polygon?crs=EPSG:4326", name, "memory")
        pr = vl.dataProvider()

        ## Add feature attributes names in the table
        pr.addAttributes([  QgsField("start_x", QVariant.Double),
                            QgsField("start_y", QVariant.Double),
                            QgsField("mode", QVariant.String),
                            QgsField("range", QVariant.Int),
                            QgsField("unit", QVariant.String)
                        ])
        vl.updateFields()
        
        ## For every point selected or just for this one clicked
        for sc in selectedCoords:
            if self.requestAPI(sc) != 'keyerror':  

                queryString, dist, unit = self.createSkobblerURL(sc) if self.dlg.radioButton.isChecked() else self.createHereURL(sc) # to get params from URL

                ## Create geometry from points
                points = []
                if self.dlg.radioButton.isChecked(): # if Skobbler
                    x = [(self.coordsResponse[i]) for i in range(1, len(self.coordsResponse), 2)]
                    y = [(self.coordsResponse[i]) for i in range(0, len(self.coordsResponse), 2)]
                    
                    for i, j in zip(y[4:], x[4:]):
                        points.append(QgsPoint(i,j))

                else: # if HERE
                    coordsHERE = [map(float,i.split(',')) for i in self.coordsResponse]
                    x = [(coordsHERE[i][0]) for i in range(len(coordsHERE))]
                    y = [(coordsHERE[i][1]) for i in range(len(coordsHERE))]
                    
                    for i, j in zip(y, x):
                        points.append(QgsPoint(i,j))            

                fet = QgsFeature()
                fet.setGeometry(QgsGeometry.fromPolygon([points]))

                ## Set feature name/attribute
                fet.setAttributes([
                                sc.x(),
                                sc.y(),
                                self.transportation,
                                self.dlg.spinBox.value(),                        
                                ('meters' if self.dlg.radioButton_4.isChecked() else 'minutes')
                                ])

                pr.addFeatures([fet])
                vl.updateExtents()
            else:
                self.iface.messageBar().pushMessage("Error", "Invalid starting point - no roads around", level=QgsMessageBar.WARNING, duration=5)

        ## Add prepared layer with transparency
        QgsMapLayerRegistry.instance().addMapLayer(vl)
        vl.setLayerTransparency(50)

    def saveKeys(self):
        """ Save API keys to global QGIS settings, so user doesn't need to input it every time """
        skobb = 'none' if self.dlg.lineEdit.text() == '' else self.dlg.lineEdit.text()
        here = 'none' if self.dlg.lineEdit_2.text() == '' else self.dlg.lineEdit_2.text()

        s = QSettings()
        s.setValue("catchment/skobbler_key",skobb)
        s.setValue("catchment/here_key",here)

    def loadMapTool(self):
        """ Set EmitPoint with CrossCursor as MapTool """
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        self.canvas.setMapTool(self.clickTool)
        QObject.connect(self.clickTool, SIGNAL("canvasClicked(const QgsPoint &, Qt::MouseButton)"), self.selectCoord)

    def bringBackCursor(self):
        """ Restore Pan map tool instead of EmitPoint tool with CrossCursor """ 
        self.clickTool = QgsMapToolPan(self.canvas)
        self.canvas.setMapTool(self.clickTool)

    def runOrPass(self):
        """ Check if anything was selected to help handle 'pass' on result """
        layer = self.iface.activeLayer()
        if layer.selectedFeatureCount() > 0:
            return True

    def run(self):
        """Run method that performs all the real work"""

        ## Clear geocoding box
        self.dlg.textBrowser.clear()

        ## Set EmitPoint as MapTool
        self.loadMapTool()

        ## show the dialog
        self.dlg.show()
        
        ## Radio/Checkboxes manipulation
        self.dlg.radioButton.toggled.connect(self.toggleProvider)
        self.dlg.radioButton_3.toggled.connect(self.checkBoxes)

        ## Run the dialog event loop
        result = self.dlg.exec_()

        ## See if OK was pressed
        if result:            

            if self.dlg.textBrowser.toPlainText() != '' or self.runOrPass() == True: # if geocoding not empty = if mouse was clicked anywhere
                self.chooseCoords() # the main trigger here
            else:
                pass

        ## Restore default cursor
        self.bringBackCursor()