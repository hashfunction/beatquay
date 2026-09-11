// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
// Only the standalone harness: model the GUI-less application boundary and
// uninitialized Engine, not configuration/path behavior. The native suite links
// the real lmmsobjs implementations instead.
#include "Engine.h"
#include "GuiApplication.h"
#include "MainWindow.h"
lmms::Song* lmms::Engine::s_song = nullptr;
lmms::gui::GuiApplication* lmms::gui::getGUI() { return nullptr; }
const QMetaObject lmms::gui::MainWindow::staticMetaObject = QMainWindow::staticMetaObject;
