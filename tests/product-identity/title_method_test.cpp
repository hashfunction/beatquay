// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
// Compile the exact production title method against a GUI-free model boundary.
#include <QFileInfo>
#include <QtTest>
#include "lmmsversion.h"
#include "BeatQuayIdentity.h"
namespace lmms::gui
{
struct SongState
{
    QString path;
    bool modified = false;
    QString projectFileName() const { return path; }
    bool isModified() const { return modified; }
};
struct Engine { static SongState* getSong() { static SongState song; return &song; } };
enum class SessionState { Normal, Recover };
class MainWindow : public QObject
{
public:
    QString title;
    SessionState session = SessionState::Normal;
    SessionState getSession() const { return session; }
    void setWindowTitle(const QString& value) { title = value; }
    void resetWindowTitle();
};
#include "production_title_method.inc"
}
class BeatQuayTitleMethodTest : public QObject
{
    Q_OBJECT
private slots:
    void titleStates()
    {
        using namespace lmms::gui;
        MainWindow window;
        auto song = Engine::getSong();
        window.resetWindowTitle();
        QCOMPARE(window.title, QString("BeatQuay 1.0.0"));
        song->path = "/chosen/音楽.mmp";
        window.resetWindowTitle();
        QCOMPARE(window.title, QString::fromUtf8("音楽 - BeatQuay 1.0.0"));
        song->modified = true;
        window.resetWindowTitle();
        QCOMPARE(window.title, QString::fromUtf8("音楽* - BeatQuay 1.0.0"));
        window.session = SessionState::Recover;
        window.resetWindowTitle();
        QVERIFY(window.title.contains("Recover session. Please save your work!"));
        QVERIFY(window.title.endsWith(" - BeatQuay 1.0.0"));
    }
};
QTEST_GUILESS_MAIN(BeatQuayTitleMethodTest)
#include "title_method_test.moc"
