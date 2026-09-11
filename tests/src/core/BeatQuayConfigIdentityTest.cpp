// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QProcess>
#include <QProcessEnvironment>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QtTest>
#include "ConfigManager.h"

static QByteArray read(const QString& path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly)) { return {}; }
    return file.readAll();
}

static bool write(const QString& path, const QByteArray& bytes)
{
    QFile file(path);
    return file.open(QIODevice::WriteOnly | QIODevice::NewOnly) && file.write(bytes) == bytes.size();
}

// The probe is copied to its own application directory, with a fresh home.
// It executes real ConfigManager loading/saving; it never initializes audio/GUI.
static int probe(const QString& mode)
{
    const QString home = QDir::homePath();
    const QString app = QCoreApplication::applicationDirPath();
    const QString oldWork = home + "/lmms/";
    if (!QDir().mkpath(oldWork + "projects")) { return 20; }
    const QByteArray sentinel = ("<lmms version=\"1.3.0\" configversion=\"3\"><sentinel upstream=\"must-not-load\"/>"
        "<paths workingdir=\"" + oldWork.toUtf8() + "\"/></lmms>");
    const QString oldConfig = (mode == "installed" ? home : app) + "/.lmmsrc.xml";
    if (!write(oldConfig, sentinel)) { return 21; }
    if (mode == "development")
    {
        if (!write(app + "/CMakeCache.txt", ("lmms_SOURCE_DIR:STATIC=" + app +
            "\nlmms_BINARY_DIR:STATIC=" + app + "\n").toUtf8())) { return 22; }
    }
    auto config = lmms::ConfigManager::inst();
    if (mode == "portable") { config->initPortableWorkingDir(); }
    if (mode == "installed") { config->initInstalledWorkingDir(); }
    if (mode == "development") { config->initDevelopmentWorkingDir(); }
    const QString expectedWork = mode == "portable" ? app + "/beatquay-workspace/" :
        QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation) + "/BeatQuay/";
    if (config->workingDir() != expectedWork)
    {
        qCritical() << "Unexpected working directory" << config->workingDir() << expectedWork; return 2;
    }
    // Windows DocumentsLocation is a known folder and may ignore USERPROFILE.
    // Validate its selected default above, then keep every loader mkdir under
    // the owned home, even if a developer already has a BeatQuay workspace.
    config->setWorkingDir(home + "/uncreated-probe-work/");
    config->loadConfigFile();
    if (!config->value("sentinel", "upstream").isEmpty())
    {
        qCritical("Default loaded upstream LMMS sentinel"); return 1;
    }
    config->saveConfigFile();
    const QString ownConfig = (mode == "installed" ? home : app) + "/.beatquayrc.xml";
    if (!QFile::exists(ownConfig) || read(oldConfig) != sentinel) { return 3; }
    // Explicit upstream-compatible config remains opt-in and writable.
    const QString explicitConfig = home + "/chosen-config.xml";
    if (!write(explicitConfig, sentinel)) { return 23; }
    config->loadConfigFile(explicitConfig);
    if (config->value("sentinel", "upstream") != "must-not-load" || config->workingDir() != oldWork) { return 4; }
    config->setValue("sentinel", "explicit", "saved");
    config->saveConfigFile();
    if (!read(explicitConfig).contains("explicit=\"saved\"") || read(oldConfig) != sentinel) { return 5; }
    return 0;
}

class BeatQuayConfigIdentityTest : public QObject
{
    Q_OBJECT
private slots:
    void isolatedDefaults_data()
    {
        QTest::addColumn<QString>("mode");
        for (const auto mode : {"installed", "portable", "development"}) { QTest::newRow(mode) << QString(mode); }
    }
    void isolatedDefaults()
    {
        QFETCH(QString, mode);
        QTemporaryDir root;
        QVERIFY(root.isValid());
        QVERIFY(QDir(root.path()).mkpath("home"));
        QVERIFY(QDir(root.path()).mkpath("app"));
        const QString child = root.filePath("app/" + QFileInfo(QCoreApplication::applicationFilePath()).fileName());
        QVERIFY(QFile::copy(QCoreApplication::applicationFilePath(), child));
        auto env = QProcessEnvironment::systemEnvironment();
        env.insert("HOME", root.filePath("home"));
        env.insert("USERPROFILE", root.filePath("home"));
        // Qt/other DLLs remain available to a copied native test host on Windows.
        env.insert("PATH", QCoreApplication::applicationDirPath() + QDir::listSeparator() + env.value("PATH"));
        QProcess process;
        process.setProcessEnvironment(env);
        process.start(child, {"--config-identity-probe", mode});
        QVERIFY(process.waitForStarted());
        QVERIFY(process.waitForFinished(30000));
        QCOMPARE(process.exitStatus(), QProcess::NormalExit);
        const auto diagnostics = process.readAllStandardError();
        QVERIFY2(process.exitCode() == 0, diagnostics.constData());
    }
};

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);
    if (app.arguments().size() == 3 && app.arguments()[1] == "--config-identity-probe") { return probe(app.arguments()[2]); }
    BeatQuayConfigIdentityTest test;
    return QTest::qExec(&test, argc, argv);
}
#include "BeatQuayConfigIdentityTest.moc"
