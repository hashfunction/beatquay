# Copyright 2026 Trieflow LLC. MIT.
# Standalone real Qt route probe. Requires PyQt6; not a substitute for installed Windows UIA.
from PyQt6.QtCore import Qt,QPoint
from PyQt6.QtWidgets import QApplication,QMdiArea,QMdiSubWindow,QMainWindow,QPushButton,QLabel
from PyQt6.QtTest import QTest
from PyQt6.QtCore import qVersion
app=QApplication([]);app.setStyle("Fusion")
main=QMainWindow();main.setWindowTitle("BeatQuay 1.0.0");main.menuBar().addMenu("File")
area=QMdiArea();main.setCentralWidget(area);main.resize(1000,700);main.show()
sub=QMdiSubWindow();area.addSubWindow(sub)
content=QMainWindow();sub.setWidget(content)
sub.setWindowTitle('Song-Editor')
sub.setWindowFlags((sub.windowFlags() & ~Qt.WindowType.WindowMinimizeButtonHint)|Qt.WindowType.CustomizeWindowHint)
label=QLabel('Song-Editor',sub);label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents);label.move(25,4)
for i,text in enumerate(['Close','Maximize','Detach']):
 button=QPushButton('',sub);button.setToolTip(text);button.resize(17,17);button.move(313-i*18,3);button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
area.show();sub.show();sub.resize(333,163);app.processEvents()
pt=QPoint(sub.width()//2,content.y()//2)
assert not sub.isMaximized() and 18<=content.y()<=40
QTest.mouseMove(sub,pt);QTest.mouseClick(sub,Qt.MouseButton.LeftButton,pos=pt);QTest.mouseDClick(sub,Qt.MouseButton.LeftButton,pos=pt);app.processEvents()
assert sub.isMaximized(),(sub.geometry(),pt)
assert sub.geometry()==area.viewport().rect(),(sub.geometry(),area.viewport().rect())
print('MAIN TITLE',main.windowTitle());print('PASS Qt runtime',qVersion(),'real QMdiSubWindow inherited title-bar double-click; maximized geometry',sub.geometry().getRect(),'content',content.geometry().getRect())
for title in ['Untitled* - BeatQuay 1.0.0','Evening Pulse - BeatQuay 1.0.0','BeatQuay 1.0.0']:
 main.setWindowTitle(title);app.processEvents()
 print('UPDATED TITLE',main.windowTitle())
 assert main.windowTitle()==title+' - [Song-Editor]'
area.close()
