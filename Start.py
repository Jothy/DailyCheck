import sys

from PyQt5 import QtCore, QtGui, QtWidgets,Qt
import time, datetime, os

from MainWindow import Ui_MainWindow
import ScriptDataFrame as DB
import matplotlib.pyplot as plt


import numpy as np
import dicom as dcm
from pylinac.flatsym import BeamImage
import glob
import datetime as dt


class StartQT(QtWidgets.QDialog):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        try:
            self.LoadSettings()
        except:
            pass

        date = datetime.date.today()
        if date.month<10:
            month ="0"+str(date.month)
        else:
            month =str(date.month)
        if date.day<10:
            day ="0"+str(date.day)
        else:
            day =str(date.day)
        today=str(date.year)+month+day
        directory=str(self.ui.lineEditImageFolder.text())+'\\'+str(self.ui.comboBoxLA.currentText())+'\\'+today
        #print(self.ui.lineEditImageFolder.text())
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except:
            pass

        self.ui.calendarWidget.setFocus()#Cursor on todays date
        self.CurOutput=0.0
        self.CurFlatX=0.0
        self.CurFlatY=0.0
        self.CurSymX=0.0
        self.CurSymY=0.0
        self.Slope6X=0.0
        self.Intercept6X=0.0
        self.Slope18X=0.0
        self.Intercept18X=0.0
        self.Slope6XSRS=0.0
        self.Intercept6XSRS=0.0
        self.MPV=0.0
        self.CurEnergy=''
        self.ImgFolder=self.ui.lineEditImageFolder.text()
        self.CurFile=''
        self.Date=list()
        self.Password='DailyCheck123'
        self.GetCurrentDate()
        self.LoopToogle=True
        self.CurDate=''
        self.BatchMode=True
        self.Blink=True
        self.ui.tableWidget.setAlternatingRowColors(True)
        self.CurR2=0.0#Correlation Coefficient
        self.CurDoseRate=0.0

        self.CurCalibIntercept=''
        self.CurCalibSlope=''
        self.CurCalibEnergy=''



        #self.navi_toolbar1 = NavigationToolbar(self.ui.CalibrationPlot,self)
        self.ui.pushButtonStart.clicked.connect(self.StartLoop)
        self.ui.pushButtonStop.clicked.connect(self.StopLoop)
        self.ui.pushButtonLogin.clicked.connect(self.Login)
        self.ui.pushButtonLogout.clicked.connect(self.Logout)
        self.ui.checkBoxBatchAnalyse.clicked.connect(self.ChangeMode)
        self.ui.tableWidget.cellChanged.connect(self.ColorCells)
        self.ui.pushButtonToXLS.clicked.connect(self.ConvertToXLS)
        self.ui.pushButtonLoadImages.clicked.connect(self.Calibrate)
        self.ui.lineEditImageFolder.textEdited.connect(self.ChooseFolder)
        self.ui.lineEditDBFile.textEdited.connect(self.ChooseDBFile)
        self.ui.pushButton.clicked.connect(self.UpdateCalibration)
        self.ui.buttonBox.accepted.connect(self.PushResultsToDB)
        self.ui.buttonBox.rejected.connect(self.Exit)

        #Start looking for new files automatically
        #self.StartLoop()

        #Only required to create new DB file
        # tt=DB.CreateTable()
        # DB.SaveTable(tt,'D:\DailyCheck\DailyQA')



    #Check for new file in a folder
    def CheckForNewFile(self):
        self.ImgFolder = self.ImgFolder+"\\"+self.CurDate
        #print(self.ImgFolder)
        before = dict ([(f, None) for f in os.listdir (self.ImgFolder)])
        while self.LoopToogle==True:
          time.sleep (1)
          after = dict ([(f, None) for f in os.listdir (self.ImgFolder)])
          added = [f for f in after if not f in before]
          #removed = [f for f in before if not f in after]
          if added:
              #print("Added: ", ", ".join (added))
              self.CurFile=self.ImgFolder+"\\"+added[0]
              #print(self.CurFile)
              ds=dcm.read_file(self.CurFile)
              Energy = int(ds.ExposureSequence[0].data_element('KVP').value) / 1000
              self.CurDoseRate = ds.RTImageDescription.split(',')[1].split(('\r'))[0].split(' ')[1]  # MU/min
              # print(self.CurDoseRate,':Dose rate')
              if Energy == 6.0 and self.CurDoseRate == '600':
                  self.CurEnergy = '6X'
                  # print(Energy,'6X')
              elif Energy == 18.0 and self.CurDoseRate == '600':
                  self.CurEnergy = '18X'
              elif Energy == 6.0 and self.CurDoseRate == '1000':
                  self.CurEnergy = '6XSRS'

              self.ui.groupBox.setTitle(self.CurEnergy)
              self.AnalyseImage()
              self.CalcOutput()
              self.ColorResults()
              self.AddRowToTable()
          #if removed: print("Removed: ", ", ".join (removed))
          before = after
          QtGui.QApplication.processEvents()
        return before

    def BatchAnalyseFiles(self):
        self.ImgFolder = self.ImgFolder+"\\"+self.ui.comboBoxLA.currentText()+"\\"+self.CurDate
        FilesList=glob.glob(self.ImgFolder+"\*.DCM")
        for x in range(0,np.size(FilesList),1):
            self.CurFile=FilesList[x]
            ds=dcm.read_file(self.CurFile)
            #kVP to MV conversion
            Energy=int(ds.ExposureSequence[0].data_element('KVP').value)/1000
            self.CurDoseRate=ds.RTImageDescription.split(',')[1].split(('\r'))[0].split(' ')[1]#MU/min
            #print(self.CurDoseRate,':Dose rate')
            if Energy==6.0 and self.CurDoseRate=='600':
                self.CurEnergy='6X'
                #print(Energy,'6X')
            elif Energy==18.0 and self.CurDoseRate=='600':
                self.CurEnergy='18X'
            elif Energy==6.0 and self.CurDoseRate=='1000':
                self.CurEnergy='6XSRS'
            #print(self.CurEnergy,':Energy')
            self.ui.groupBox.setTitle(self.CurEnergy)
            self.AnalyseImage()
            self.CalcOutput()
            self.ColorResults()
            self.AddRowToTable()
        self.ui.tabWidget.setCurrentIndex(1)
        QtGui.QApplication.processEvents()

    def ColorResults(self):
        #Output
        if self.CurOutput<=2.0:
            self.ui.labelOutput.setStyleSheet("QLabel {background-color:green}")
        elif self.CurOutput>2.0 and self.CurOutput<=3.0:
            self.ui.labelOutput.setStyleSheet("QLabel {background-color:yellow}")
        elif self.CurOutput>=3.0:
            self.ui.labelOutput.setStyleSheet("QLabel {background-color:red}")

        #FlatX
        if self.CurFlatX<=2.0:
            self.ui.labelFlatX.setStyleSheet("QLabel {background-color:green}")
        elif self.CurFlatX>2.0 and self.CurFlatX<=3.0:
            self.ui.labelFlatX.setStyleSheet("QLabel {background-color:yellow}")
        elif self.CurFlatX>=3.0:
            self.ui.labelFlatX.setStyleSheet("QLabel {background-color:red}")

        #FlatY
        if self.CurFlatY<=2.0:
            self.ui.labelFlatY.setStyleSheet("QLabel { background-color:green}")
        elif self.CurFlatY>2.0 and self.CurFlatY<=3.0:
            self.ui.labelFlatY.setStyleSheet("QLabel { background-color:yellow}")
        elif self.CurFlatY>=3.0:
            self.ui.labelFlatX.setStyleSheet("QLabel { background-color:red}")

        #SymX
        if self.CurSymX<=2.0:
            self.ui.labelSymX.setStyleSheet("QLabel { background-color:green}")
        elif self.CurSymX>2.0 and self.CurSymX<=3.0:
            self.ui.labelSymX.setStyleSheet("QLabel { background-color:yellow}")
        elif self.CurSymX>=3.0:
            self.ui.labelSymX.setStyleSheet("QLabel { background-color:red}")

        #SymY
        if self.CurSymY<=2.0:
            self.ui.labelSymY.setStyleSheet("QLabel { background-color:green}")
        elif self.CurSymY>2.0 and self.CurSymY<=3.0:
            self.ui.labelSymY.setStyleSheet("QLabel { background-color:yellow}")
        elif self.CurSymY>=3.0:
            self.ui.labelSymY.setStyleSheet("QLabel { background-color:red}")

    def GetCurrentDate(self):
        self.Date.append(QtCore.QDate.currentDate().day())
        self.Date.append(QtCore.QDate.currentDate().month())
        self.Date.append(QtCore.QDate.currentDate().year())
        #print(self.Date)

    def StartLoop(self):
        #print("Loop starting...")
        self.ui.tableWidget.setRowCount(0)
        self.BatchMode=self.ui.checkBoxBatchAnalyse.isChecked()
        self.ImgFolder=self.ui.lineEditImageFolder.text()
        self.Slope6X=float(self.ui.doubleSpinBoxSlope6X.text())
        self.Intercept6X=float(self.ui.doubleSpinBoxIntercept6X.text())
        self.Slope18X=float(self.ui.doubleSpinBoxSlope18X.text())
        self.Intercept18X=float(self.ui.doubleSpinBoxIntercept18X.text())
        self.Slope6XSRS = float(self.ui.doubleSpinBoxSlope6XSRS.text())
        self.Intercept6XSRS = float(self.ui.doubleSpinBoxIntercept6XSRS.text())
        #print(self.Slope6X,self.Slope18X,self.Intercept6X,self.Intercept18X)

        date=self.ui.calendarWidget.selectedDate()
        if date.month()<10:
            month="0"+str(date.month())
        else:
            month=str(date.month())
        if date.day()<10:
            day="0"+str(date.day())
        else:
            day=str(date.day())
        self.CurDate=str(date.year())+month+day
        if self.BatchMode==False:
            try:
                self.CurFile=self.CheckForNewFile()
            except:
                pass
        elif self.BatchMode==True:
            self.BatchAnalyseFiles()
        #Show the results page after analyses
        self.ui.tabWidget.setCurrentIndex(1)

    def ChangeMode(self):
        self.BatchMode=self.ui.checkBoxBatchAnalyse.isChecked()
        #print(self.BatchMode)

    def StopLoop(self):
        #print("Stopping loop...")
        self.LoopToogle=False

    def AnalyseImage(self):
            Img=BeamImage(self.CurFile)
            self.CurFlatX=abs(Img.flatness(plane='both')[0])
            self.CurFlatY=abs(Img.flatness(plane='both')[1])
            self.CurSymX=abs(Img.symmetry(plane='both')[0])
            self.CurSymY=abs(Img.symmetry(plane='both')[1])
            self.CurOutput=1.0
            self.ColorResults()

    def Login(self):
        password=QtGui.QInputDialog.getText(self, "Enter Password", "Password:",QtGui.QLineEdit.Password)[0]
        #print(password,self.Password)
        if password==self.Password:
            self.ui.doubleSpinBoxSlope6X.setEnabled(True)
            self.ui.doubleSpinBoxIntercept6X.setEnabled(True)
            self.ui.doubleSpinBoxSlope18X.setEnabled(True)
            self.ui.doubleSpinBoxIntercept18X.setEnabled(True)
            self.ui.lineEditImageFolder.setEnabled(True)
            self.ui.comboBoxLA.setEnabled(True)
        else:
            self.ui.doubleSpinBoxSlope6X.setEnabled(False)
            self.ui.doubleSpinBoxIntercept6X.setEnabled(False)
            self.ui.doubleSpinBoxSlope18X.setEnabled(False)
            self.ui.doubleSpinBoxIntercept18X.setEnabled(False)
            self.ui.lineEditImageFolder.setEnabled(False)
            self.ui.comboBoxLA.setEnabled(False)

    def Logout(self):
        self.ui.doubleSpinBoxSlope6X.setEnabled(False)
        self.ui.doubleSpinBoxIntercept6X.setEnabled(False)
        self.ui.doubleSpinBoxSlope18X.setEnabled(False)
        self.ui.doubleSpinBoxIntercept18X.setEnabled(False)
        self.ui.lineEditImageFolder.setEnabled(False)
        self.ui.comboBoxLA.setEnabled(False)
        self.SaveSettings()

    def AddRowToTable(self):
        rowPosition = self.ui.tableWidget.rowCount()
        self.ui.tableWidget.insertRow(rowPosition)
        self.ui.tableWidget.setItem(rowPosition,0,QtGui.QTableWidgetItem(str(self.CurEnergy)))
        self.ui.tableWidget.setItem(rowPosition,1,QtGui.QTableWidgetItem(str(np.round(self.CurOutput,2))))
        self.ui.tableWidget.setItem(rowPosition,2,QtGui.QTableWidgetItem(str(np.round(self.CurFlatX,2))))
        self.ui.tableWidget.setItem(rowPosition,3,QtGui.QTableWidgetItem(str(np.round(self.CurFlatY,2))))
        self.ui.tableWidget.setItem(rowPosition,4,QtGui.QTableWidgetItem(str(np.round(self.CurSymX,2))))
        self.ui.tableWidget.setItem(rowPosition,5,QtGui.QTableWidgetItem(str(np.round(self.CurSymY,2))))
        self.ui.tableWidget.setItem(rowPosition,6,QtGui.QTableWidgetItem(str(self.MPV)))
        self.ui.tableWidget.setItem(rowPosition,7,QtGui.QTableWidgetItem(str(self.CurDate)))
        self.ui.tableWidget.setItem(rowPosition,8, QtGui.QTableWidgetItem(dt.datetime.now().time().isoformat()))

        #Color the results
        output=np.abs(float(self.ui.tableWidget.item(rowPosition,1).text()))
        if output<=2.0:
            self.ui.tableWidget.item(rowPosition,1).setBackground(QtCore.Qt.green)
        elif output>2.0 and output <=3.0:
            self.ui.tableWidget.item(rowPosition, 1).setBackground(QtCore.Qt.yellow)
        elif output>3.0:
            self.ui.tableWidget.item(rowPosition,1).setBackground(QtCore.Qt.red)

        #FlatX
        FlatX = np.abs(float(self.ui.tableWidget.item(rowPosition,2).text()))
        if FlatX <=2.0:
            self.ui.tableWidget.item(rowPosition,2).setBackground(QtCore.Qt.green)
        elif FlatX >2.0 and FlatX <= 3.0:
            self.ui.tableWidget.item(rowPosition,2).setBackground(QtCore.Qt.yellow)
        elif FlatX >3.0:
            self.ui.tableWidget.item(rowPosition,2).setBackground(QtCore.Qt.red)

        # FlatY
        FlatY = np.abs(float(self.ui.tableWidget.item(rowPosition, 3).text()))
        if FlatY <= 2.0:
            self.ui.tableWidget.item(rowPosition, 3).setBackground(QtCore.Qt.green)
        elif FlatY >2.0 and FlatY <=3.0:
            self.ui.tableWidget.item(rowPosition, 3).setBackground(QtCore.Qt.yellow)
        elif FlatY >3.0:
            self.ui.tableWidget.item(rowPosition, 3).setBackground(QtCore.Qt.red)

        # SymX
        SymX = np.abs(float(self.ui.tableWidget.item(rowPosition,4).text()))
        if SymX <=2.0:
            self.ui.tableWidget.item(rowPosition,4).setBackground(QtCore.Qt.green)
        elif SymX >2.0 and SymX <=3.0:
            self.ui.tableWidget.item(rowPosition,4).setBackground(QtCore.Qt.yellow)
        elif SymX >3.0:
            self.ui.tableWidget.item(rowPosition,4).setBackground(QtCore.Qt.red)

        # SymY
        SymY = np.abs(float(self.ui.tableWidget.item(rowPosition,5).text()))
        if SymY <=2.0:
            self.ui.tableWidget.item(rowPosition,5).setBackground(QtCore.Qt.green)
        elif SymY >2.0 and SymY<=3.0:
            self.ui.tableWidget.item(rowPosition,5).setBackground(QtCore.Qt.yellow)
        elif SymY >3.0:
            self.ui.tableWidget.item(rowPosition,5).setBackground(QtCore.Qt.red)

        self.ui.tableWidget.update()

    def CalcOutput(self):
        #Get central pixel value
        Img=dcm.read_file(self.CurFile)
        NumOfFrames=self.GetNumFrames(self.CurFile)
        ImgData=Img._get_pixel_array()
        CentreY=ImgData.shape[0]/2
        CentreX=ImgData.shape[1]/2
        self.MPV=NumOfFrames/np.mean(ImgData[CentreY-10:CentreY+10,CentreX-10:CentreX+10])
        if self.CurEnergy=='6X':
            self.CurOutput=((self.Slope6X*self.MPV)+self.Intercept6X)/200.0
            #print(self.MPV,self.CurOutput,'6X')
        elif self.CurEnergy=='18X':
            self.CurOutput=((self.Slope18X*self.MPV)+self.Intercept18X)/200.0
        elif self.CurEnergy == '6XSRS':
            self.CurOutput = ((self.Slope6XSRS*self.MPV)+self.Intercept6XSRS)/ 200.0
            print(self.MPV,self.Slope6XSRS,self.Intercept6XSRS, self.CurOutput,'6XSRS')
        self.CurOutput=np.abs(((self.CurOutput-1.0)/1.0)*100.0)
        #print(self.CurOutput)

    def GetNumFrames(self,fp):
        Data=dcm.read_file(fp)
        Descrp=Data.RTImageDescription
        FrameStr=Descrp.split(sep='\r\n')
        Frames=FrameStr[2].split(sep='Averaged Frames')[1]
        return float(Frames)

    def GetDeliveredMU(self,fp):
        ds=dcm.read_file(fp)
        MU=ds.ExposureSequence[0].MetersetExposure
        return MU

    def ColorCells(self,r,c):
        try:
            #Output
            output=float(self.ui.tableWidget.item(r,1).text())
            if np.abs(output)<=2.0:
                self.ui.tableWidget.item(r,1).setBackground(Qt.green)
            elif np.abs(output)>1.0 and np.abs(output)<=2.0:
                self.ui.tableWidget.item(r,1).setBackground(Qt.yellow)
            elif np.abs(output)>2.0:
                self.ui.tableWidget.item(r,1).setBackground(Qt.red)
            #FlatX
            FlatX=float(self.ui.tableWidget.item(r,2).text())
            if np.abs(FlatX)<=2.0:
                self.ui.tableWidget.item(r,2).setBackground(Qt.green)
            elif np.abs(FlatX)>1.0 and np.abs(output)<=2.0:
                self.ui.tableWidget.item(r,2).setBackground(Qt.yellow)
            elif np.abs(FlatX)>2.0:
                self.ui.tableWidget.item(r,2).setBackground(Qt.red)

            #FlatY
            FlatY=float(self.ui.tableWidget.item(r,3).text())
            if np.abs(FlatY)<=2.0:
                self.ui.tableWidget.item(r,3).setBackground(Qt.green)
            elif np.abs(FlatY)>1.0 and np.abs(output)<=2.0:
                self.ui.tableWidget.item(r,3).setBackground(Qt.yellow)
            elif np.abs(FlatY)>2.0:
                self.ui.tableWidget.item(r,3).setBackground(Qt.red)

            #SymX
            SymX=float(self.ui.tableWidget.item(r,4).text())
            if np.abs(SymX)<=2.0:
                self.ui.tableWidget.item(r,4).setBackground(Qt.green)
            elif np.abs(SymX)>1.0 and np.abs(output)<=2.0:
                self.ui.tableWidget.item(r,4).setBackground(Qt.yellow)
            elif np.abs(SymX)>2.0:
                self.ui.tableWidget.item(r,4).setBackground(Qt.red)

            #SymY
            SymY=float(self.ui.tableWidget.item(r,5).text())
            if np.abs(SymY)<=2.0:
                self.ui.tableWidget.item(r,5).setBackground(Qt.green)
            elif np.abs(SymY)>1.0 and np.abs(output)<=2.0:
                self.ui.tableWidget.item(r,5).setBackground(Qt.yellow)
            elif np.abs(SymY)>2.0:
                self.ui.tableWidget.item(r,5).setBackground(Qt.red)
        except:
            pass

    def GetRowFromTable(self,r):
        ColCount=self.ui.tableWidget.columnCount()
        Results=list()
        for x in range(0,ColCount,1):
            Results.append(self.ui.tableWidget.item(r,x).text())
        return  Results

    def PushResultsToDB(self):
        InitialsDlg=QtGui.QInputDialog(self)
        InitialsDlg.setLabelText('Enter initials:')
        InitialsDlg.setWindowTitle('DailyCheck')
        InitialsDlg.exec()
        Initials=InitialsDlg.textValue()
        #print(InitialsDlg.textValue())

        DBTable=DB.ReadTable(self.ui.lineEditDBFile.text())
        NumResults=self.ui.tableWidget.rowCount()
        CurRowsInDB=DBTable.count()[1]
        if NumResults>0:
            for x in range(0,NumResults,1):
                Results=self.GetRowFromTable(x)
                curLinac=self.ui.comboBoxLA.currentText()
                Results.insert(0,curLinac)
                Results.insert(10,Initials)
                #print(Results)
                CurRowsInDB=CurRowsInDB+1
                DB.InsertRow(DBTable,CurRowsInDB,Results)

            msgBox=QtGui.QMessageBox(self)
            msgBox.setIcon(QtGui.QMessageBox.Question)
            msgBox.setText('Information')
            msgBox.setWindowTitle('DailyCheck')
            msgBox.setInformativeText("Do you want to save your results to database?")
            msgBox.setStandardButtons(QtGui.QMessageBox.Save|QtGui.QMessageBox.Discard)
            msgBox.setDefaultButton(QtGui.QMessageBox.Save)
            retval=msgBox.exec()
            if retval==2048:#equals 'save' button click
                DB.SaveTable(DBTable, str(self.ui.lineEditDBFile.text()))
                msgBox = QtGui.QMessageBox(self)
                msgBox.setIcon(QtGui.QMessageBox.Information)
                msgBox.setText('Information')
                msgBox.setWindowTitle('DailyCheck')
                msgBox.setInformativeText("Results saved to database.")
                msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
                msgBox.exec()
        else:
            msgBox = QtGui.QMessageBox(self)
            msgBox.setIcon(QtGui.QMessageBox.Critical)
            msgBox.setText('Error')
            msgBox.setWindowTitle('DailyCheck')
            msgBox.setInformativeText("No results to add!")
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.exec()

    def ConvertToXLS(self):
        DBTable=DB.ReadTable(self.ui.lineEditDBFile.text())
        DB.ConvertToXLS(DBTable,self.ui.lineEditDBFile.text()+'.xls')
        msgBox = QtGui.QMessageBox(self)
        msgBox.setIcon(QtGui.QMessageBox.Information)
        msgBox.setText('Information')
        msgBox.setWindowTitle('DailyCheck')
        msgBox.setInformativeText("Database converted to Excel format")
        msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
        msgBox.exec()

    def SaveSettings(self):
        Settings=QtCore.QSettings("TCH","DailyCheck")
        Settings.beginGroup("Calibration")
        Settings.setValue("Slope6X",self.ui.doubleSpinBoxSlope6X.value())
        Settings.setValue("Slope18X",self.ui.doubleSpinBoxSlope18X.value())
        Settings.setValue("Slope6XSRS", self.ui.doubleSpinBoxSlope6XSRS.value())
        Settings.setValue("Intercept6X",self.ui.doubleSpinBoxIntercept6X.value())
        Settings.setValue("Intercept18X",self.ui.doubleSpinBoxIntercept18X.value())
        Settings.setValue("Intercept6XSRS", self.ui.doubleSpinBoxIntercept6X.value())
        Settings.setValue("Linac",self.ui.comboBoxLA.currentIndex())
        Settings.setValue("ImgFolder",self.ui.lineEditImageFolder.text())
        Settings.setValue("DBFile",self.ui.lineEditDBFile.text())
        #print(self.ui.lineEditDBFile.text())
        Settings.endGroup()

    def LoadSettings(self):
        try:
            Settings=QtCore.QSettings("TCH","DailyCheck")
            Settings.beginGroup("Calibration")
            self.ui.doubleSpinBoxSlope6X.setValue(float(Settings.value("Slope6X")))
            self.ui.doubleSpinBoxSlope18X.setValue(float(Settings.value("Slope18X")))
            self.ui.doubleSpinBoxSlope6XSRS.setValue(float(Settings.value("Slope6XSRS")))
            self.ui.doubleSpinBoxIntercept6X.setValue(float(Settings.value("Intercept6X")))
            self.ui.doubleSpinBoxIntercept18X.setValue(float(Settings.value("Intercept18X")))
            self.ui.doubleSpinBoxIntercept6XSRS.setValue(float(Settings.value("Intercept6XSRS")))
            self.ui.comboBoxLA.setCurrentIndex(Settings.value("Linac"))
            self.ui.lineEditImageFolder.setText(Settings.value("ImgFolder"))
            self.ui.lineEditDBFile.setText(Settings.value("DBFile"))
            Settings.endGroup()
        except:
            print("Error loading settings!")
        #print(Settings.fileName())

    def SortFiles(self,FileList):
        Values = list()
        Path=FileList[0].split('SID')[0]
        for x in range(0, np.size(FileList), 1):
            Val = FileList[x].split(sep='SID')[1]
            Val = int(Val.split(sep='.dcm')[0])
            Values.append(Val)
        Values.sort()
        SortedFileList = list()
        for x in range(0, np.size(Values), 1):
            CurVal = Values[x]
            if CurVal < 10:
                CurVal = "0000" + str(CurVal)
            elif CurVal < 100:
                CurVal = "000" + str(CurVal)
            elif CurVal < 1000:
                CurVal = "00" + str(CurVal)
            elif CurVal < 10000:
                CurVal = "0" + str(CurVal)
            SortedFileList.append(Path+"SID" + CurVal + ".dcm")
        return SortedFileList

    def GetMPV(self,fp):
        NumOfFrames = self.GetNumFrames(fp)
        Img = dcm.read_file(fp)
        ImgData = Img._get_pixel_array()
        CentreY = ImgData.shape[0] / 2
        CentreX = ImgData.shape[1] / 2
        MPV = NumOfFrames / np.mean(ImgData[CentreY - 10:CentreY + 10, CentreX - 10:CentreX + 10])
        return MPV

    def Calibrate(self):
        self.ui.CalibrationPlot.axes.clear()
        self.ui.tableWidget_2.setRowCount(0)
        files =QtGui.QFileDialog(self)
        files.setWindowTitle('Calibration files')
        CalibrationImages =files.getOpenFileNames(self, caption='Select calibration files')
        CalibrationImages=self.SortFiles(CalibrationImages)
        MULst=[]
        MPVLst=[]
        for x in range(0,np.size(CalibrationImages),1):
            MU=self.GetDeliveredMU(CalibrationImages[x])
            MPV=self.GetMPV(CalibrationImages[x])
            MULst.append(MU)
            MPVLst.append(MPV)
        self.ui.tableWidget_2.setRowCount(np.size(CalibrationImages))
        for x in range(0,np.size(CalibrationImages),1):
            self.ui.tableWidget_2.setItem(x,0,QtGui.QTableWidgetItem(str(x+1)))
            self.ui.tableWidget_2.setItem(x,1,QtGui.QTableWidgetItem(str(np.round(MULst[x],1))))
            self.ui.tableWidget_2.setItem(x,2, QtGui.QTableWidgetItem(str(np.round(MPVLst[x],6))))

        coeffs=np.polyfit(MPVLst,MULst,1)
        polynomial=np.poly1d(coeffs)
        #Correlation coefficient
        self.CurR2 =np.corrcoef(MPVLst,MULst)[0,1]
        ys=polynomial(MPVLst)
        self.ui.CalibrationPlot.axes.plot(MPVLst,MULst,'o')
        self.ui.CalibrationPlot.axes.hold(True)
        self.ui.CalibrationPlot.axes.plot(MPVLst,ys)
        self.ui.CalibrationPlot.axes.set_xlabel('Mean Pixel Value')
        self.ui.CalibrationPlot.axes.set_ylabel('Delivered MU')
        self.ui.CalibrationPlot.figure.set_tight_layout(True)
        if coeffs[1]<0:
            string='-'
        else:
            string='+'
        self.ui.CalibrationPlot.axes.set_title("MU="+str(np.round(coeffs[0],2))+"*MPV"+string+str(np.abs(np.round(coeffs[1],2))))
        self.ui.CalibrationPlot.draw()
        self.CurCalibIntercept=coeffs[1]
        self.CurCalibSlope=coeffs[0]
        ds=dcm.read_file(CalibrationImages[0])
        # kVP to MV conversion
        Energy = int(ds.ExposureSequence[0].data_element('KVP').value) / 1000
        self.CurDoseRate = ds.RTImageDescription.split(',')[1].split(('\r'))[0].split(' ')[1]  # MU/min
        # print(self.CurDoseRate,':Dose rate')
        if Energy == 6.0 and self.CurDoseRate == '600':
            self.CurCalibEnergy = '6X'
            # print(Energy,'6X')
        elif Energy == 18.0 and self.CurDoseRate == '600':
            self.CurCalibEnergy = '18X'
        elif Energy == 6.0 and self.CurDoseRate == '1000':
            self.CurCalibEnergy = '6XSRS'

    def UpdateCalibration(self):
        if self.CurR2>0.98:
            self.Login()
            #print(self.CurCalibEnergy)
            if self.CurCalibEnergy=='6X':
                self.ui.doubleSpinBoxIntercept6X.setValue(self.CurCalibIntercept)
                self.ui.doubleSpinBoxSlope6X.setValue(self.CurCalibSlope)
            elif self.CurCalibEnergy=='18X':
                self.ui.doubleSpinBoxIntercept18X.setValue(self.CurCalibIntercept)
                self.ui.doubleSpinBoxSlope18X.setValue(self.CurCalibSlope)
            elif self.CurCalibEnergy=='6XSRS':
                self.ui.doubleSpinBoxIntercept6XSRS.setValue(self.CurCalibIntercept)
                self.ui.doubleSpinBoxSlope6XSRS.setValue(self.CurCalibSlope)
                print(self.CurCalibIntercept,self.CurCalibSlope,"Intercept,Slope")
            self.Logout()
        else:
            msgBox = QtGui.QMessageBox(self)
            msgBox.setIcon(QtGui.QMessageBox.Critical)
            msgBox.setText('Error in calibration')
            msgBox.setWindowTitle('DailyCheck')
            msgBox.setInformativeText("R<sup>2</sup> is less than 0.98. Please check the uploaded calibration files.")
            msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
            msgBox.exec()

    def ChooseFolder(self):
        DirChosen=QtGui.QFileDialog.getExistingDirectory(self)
        self.ui.lineEditImageFolder.setText(DirChosen)

    def ChooseDBFile(self):
        FileChosen=QtGui.QFileDialog.getOpenFileName(self)
        self.ui.lineEditDBFile.setText(FileChosen)

    def Exit(self):
        self.StopLoop()
        self.close()

    def closeEvent(self,event):
        self.StopLoop()
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myapp = StartQT()
    myapp.show()
    myapp.setWindowTitle('DailyCheck')
    sys.exit(app.exec_())

