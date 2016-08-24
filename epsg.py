from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform

def EPSG(self):
    currentEPSG = self.canvas.mapRenderer().destinationCrs().authid()
    if currentEPSG != 'EPSG:4326':
        crsSrc = QgsCoordinateReferenceSystem(int(currentEPSG[5:]))
        crsDest = QgsCoordinateReferenceSystem(4326) ## WGS-84
        xform = QgsCoordinateTransform(crsSrc, crsDest)
        self.selectedCoords = xform.transform(self.pntGeom.asPoint())