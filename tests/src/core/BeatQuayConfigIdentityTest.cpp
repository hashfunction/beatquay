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
#include <cstdio>
#include "ConfigManager.h"

// Windows GUI-subsystem builds can send Qt diagnostics to the debugger instead
// of QProcess's stderr pipe. Keep this test boundary on the C stderr stream.
static void diagnostic(const QString& message)
{
    std::fprintf(stderr, "%s\n", message.toUtf8().constData());
    std::fflush(stderr);
}

static QByteArray read(const QString& path)
{
    QFile file(path);
    if (!file.open(QIODevice::ReadOnly))
    {
        diagnostic(QString("read failed path=%1 error=%2").arg(path, file.errorString()));
        return {};
    }
    return file.readAll();
}

static bool write(const QString& path, const QByteArray& bytes)
{
    QFile file(path);
    const bool success = file.open(QIODevice::WriteOnly | QIODevice::NewOnly) && file.write(bytes) == bytes.size();
    if (!success) { diagnostic(QString("exclusive write failed path=%1 error=%2").arg(path, file.errorString())); }
    return success;
}

// The probe is copied to its own application directory, with owned fixture data.
// It executes real ConfigManager loading/saving; it never initializes audio/GUI.
static int probe(const QString& mode)
{
    const QString platformHome = QDir::homePath();
    const QString home = qEnvironmentVariable("BEATQUAY_TEST_HOME");
    const QString app = QCoreApplication::applicationDirPath();
    diagnostic(QString("probe start mode=%1 requestedHome=%2 actualQtHome=%3 app=%4").arg(mode, home, platformHome, app));
    const auto fail = [&mode](int code, const QString& reason)
    {
        diagnostic(QString("probe failure mode=%1 exit=%2: %3").arg(mode).arg(code).arg(reason));
        return code;
    };
    // Windows Qt can ignore USERPROFILE/HOME in favor of the token's profile.
    // Never open/mkdir there. Require the parent's existing fixture home beside
    // the copied application, independent of Qt's selected platform home.
    const QFileInfo fixtureHome(home);
    if (home.isEmpty() || !fixtureHome.isDir() || fixtureHome.isSymLink() ||
        fixtureHome.canonicalFilePath() != QFileInfo(app + "/../home").canonicalFilePath())
    {
        return fail(24, "invalid owned fixture home");
    }
    const QString oldWork = home + "/lmms/";
    if (!QDir().mkpath(oldWork + "projects")) { return fail(20, "create upstream workspace path=" + oldWork); }
    const QByteArray sentinel = ("<lmms version=\"1.3.0\" configversion=\"3\"><sentinel upstream=\"must-not-load\"/>"
        "<paths workingdir=\"" + oldWork.toUtf8() + "\"/></lmms>");
    const QString oldConfig = (mode == "installed" ? home : app) + "/.lmmsrc.xml";
    if (!write(oldConfig, sentinel)) { return fail(21, "create upstream sentinel path=" + oldConfig); }
    if (mode == "development")
    {
        if (!write(app + "/CMakeCache.txt", ("lmms_SOURCE_DIR:STATIC=" + app +
            "\nlmms_BINARY_DIR:STATIC=" + app + "\n").toUtf8())) { return fail(22, "create development cache path=" + app); }
    }
    auto config = lmms::ConfigManager::inst();
    if (mode == "portable") { config->initPortableWorkingDir(); }
    if (mode == "installed") { config->initInstalledWorkingDir(); }
    if (mode == "development") { config->initDevelopmentWorkingDir(); }
    const QString expectedWork = mode == "portable" ? app + "/beatquay-workspace/" :
        QStandardPaths::writableLocation(QStandardPaths::DocumentsLocation) + "/BeatQuay/";
    if (config->workingDir() != expectedWork)
    {
        return fail(2, QString("working directory actual=%1 expected=%2").arg(config->workingDir(), expectedWork));
    }
    const QString expectedDefaultConfig = (mode == "installed" ? platformHome : app) + "/.beatquayrc.xml";
    diagnostic(QString("selected config actual=%1 expected=%2").arg(config->configFilePath(), expectedDefaultConfig));
    if (QDir::fromNativeSeparators(config->configFilePath()) != expectedDefaultConfig)
    {
        return fail(6, "unexpected default configuration path");
    }
    // Windows DocumentsLocation is a known folder and may ignore USERPROFILE.
    // Validate defaults above without opening the installed user's settings.
    // Portable/development still exercise their real default file, in the
    // copied app. Installed IO explicitly selects an owned fixture file.
    config->setWorkingDir(home + "/uncreated-probe-work/");
    const QString ownConfig = (mode == "installed" ? home : app) + "/.beatquayrc.xml";
    config->loadConfigFile(mode == "installed" ? ownConfig : QString());
    if (!config->value("sentinel", "upstream").isEmpty())
    {
        return fail(1, "default loaded upstream LMMS sentinel");
    }
    config->saveConfigFile();
    const bool ownConfigExists = QFile::exists(ownConfig);
    const bool originalUnchanged = read(oldConfig) == sentinel;
    if (!ownConfigExists || !originalUnchanged)
    {
        return fail(3, QString("default save ownPath=%1 exists=%2 upstreamPath=%3 unchanged=%4")
            .arg(ownConfig).arg(ownConfigExists).arg(oldConfig).arg(originalUnchanged));
    }
    // Explicit upstream-compatible config remains opt-in and writable.
    const QString explicitConfig = home + "/chosen-config.xml";
    if (!write(explicitConfig, sentinel)) { return fail(23, "create explicit config path=" + explicitConfig); }
    config->loadConfigFile(explicitConfig);
    if (config->value("sentinel", "upstream") != "must-not-load" || config->workingDir() != oldWork)
    {
        return fail(4, QString("explicit load path=%1 sentinelMatches=%2 workingDir=%3 expected=%4")
            .arg(explicitConfig).arg(config->value("sentinel", "upstream") == "must-not-load")
            .arg(config->workingDir(), oldWork));
    }
    config->setValue("sentinel", "explicit", "saved");
    config->saveConfigFile();
    const bool explicitSaved = read(explicitConfig).contains("explicit=\"saved\"");
    const bool originalStillUnchanged = read(oldConfig) == sentinel;
    if (!explicitSaved || !originalStillUnchanged)
    {
        return fail(5, QString("explicit save path=%1 saved=%2 upstreamPath=%3 unchanged=%4")
            .arg(explicitConfig).arg(explicitSaved).arg(oldConfig).arg(originalStillUnchanged));
    }
    return 0;
}

class BeatQuayConfigIdentityTest : public QObject
{
    Q_OBJECT
private slots:
    void childFailureDiagnostics()
    {
        QTemporaryDir root;
        QVERIFY(root.isValid());
        QVERIFY(QDir(root.path()).mkpath("home"));
        QVERIFY(QDir(root.path()).mkpath("app"));
        const QString child = root.filePath("app/" + QFileInfo(QCoreApplication::applicationFilePath()).fileName());
        QVERIFY(QFile::copy(QCoreApplication::applicationFilePath(), child));
        const QString collision = root.filePath("app/.lmmsrc.xml");
        const QByteArray original = "preexisting config must survive";
        QVERIFY(write(collision, original));
        auto env = QProcessEnvironment::systemEnvironment();
        env.insert("BEATQUAY_TEST_HOME", root.filePath("home"));
        env.insert("HOME", root.filePath("home"));
        env.insert("USERPROFILE", root.filePath("home"));
        env.insert("PATH", QCoreApplication::applicationDirPath() + QDir::listSeparator() + env.value("PATH"));
        QProcess process;
        process.setProcessEnvironment(env);
        process.start(child, {"--config-identity-probe", "portable"});
        QVERIFY(process.waitForStarted());
        QVERIFY(process.waitForFinished(30000));
        QCOMPARE(process.exitStatus(), QProcess::NormalExit);
        QCOMPARE(process.exitCode(), 21);
        const auto diagnostics = process.readAllStandardError();
        QVERIFY2(diagnostics.contains("probe completed mode=portable exit=21"), diagnostics.constData());
        QVERIFY2(diagnostics.contains("create upstream sentinel"), diagnostics.constData());
        QVERIFY2(diagnostics.contains(collision.toUtf8()), diagnostics.constData());
        QCOMPARE(read(collision), original);
        env.remove("BEATQUAY_TEST_HOME");
        process.setProcessEnvironment(env);
        process.start(child, {"--config-identity-probe", "portable"});
        QVERIFY(process.waitForStarted());
        QVERIFY(process.waitForFinished(30000));
        QCOMPARE(process.exitStatus(), QProcess::NormalExit);
        QCOMPARE(process.exitCode(), 24);
        QVERIFY(process.readAllStandardError().contains("invalid owned fixture home"));
        QCOMPARE(read(collision), original);
    }
    void isolatedDefaults_data()
    {
        QTest::addColumn<QString>("mode");
        QTest::addColumn<bool>("differentPlatformHome");
        for (const auto mode : {"installed", "portable", "development"})
        {
            QTest::newRow(mode) << QString(mode) << false;
            QTest::newRow(qPrintable(QString(mode) + "-different-platform-home")) << QString(mode) << true;
        }
    }
    void isolatedDefaults()
    {
        QFETCH(QString, mode);
        QFETCH(bool, differentPlatformHome);
        QTemporaryDir root;
        QVERIFY(root.isValid());
        QVERIFY(QDir(root.path()).mkpath("home"));
        QVERIFY(QDir(root.path()).mkpath("app"));
        QVERIFY(QDir(root.path()).mkpath("platform-home"));
        const QByteArray untouched = "unrelated platform-home contents must survive";
        for (const auto name : {".lmmsrc.xml", ".beatquayrc.xml", "chosen-config.xml"})
        {
            QVERIFY(write(root.filePath("platform-home/" + QString(name)), untouched));
        }
        const QString child = root.filePath("app/" + QFileInfo(QCoreApplication::applicationFilePath()).fileName());
        QVERIFY(QFile::copy(QCoreApplication::applicationFilePath(), child));
        auto env = QProcessEnvironment::systemEnvironment();
        env.insert("BEATQUAY_TEST_HOME", root.filePath("home"));
        env.insert("HOME", root.filePath(differentPlatformHome ? "platform-home" : "home"));
        env.insert("USERPROFILE", env.value("HOME"));
        // Qt/other DLLs remain available to a copied native test host on Windows.
        env.insert("PATH", QCoreApplication::applicationDirPath() + QDir::listSeparator() + env.value("PATH"));
        QProcess process;
        process.setProcessEnvironment(env);
        process.start(child, {"--config-identity-probe", mode});
        QVERIFY(process.waitForStarted());
        QVERIFY(process.waitForFinished(30000));
        const auto diagnostics = QString("mode=%1 exit=%2 status=%3 processError=%4\nstderr:\n%5\nstdout:\n%6")
            .arg(mode).arg(process.exitCode()).arg(static_cast<int>(process.exitStatus()))
            .arg(process.errorString(), QString::fromUtf8(process.readAllStandardError()),
                QString::fromUtf8(process.readAllStandardOutput())).toUtf8();
        for (const auto name : {".lmmsrc.xml", ".beatquayrc.xml", "chosen-config.xml"})
        {
            QCOMPARE(read(root.filePath("platform-home/" + QString(name))), untouched);
        }
        QVERIFY2(!QFile::exists(root.filePath("platform-home/lmms")), diagnostics.constData());
        QVERIFY2(process.exitStatus() == QProcess::NormalExit, diagnostics.constData());
        QVERIFY2(process.exitCode() == 0, diagnostics.constData());
    }
};

int main(int argc, char** argv)
{
    QCoreApplication app(argc, argv);
    if (app.arguments().size() == 3 && app.arguments()[1] == "--config-identity-probe")
    {
        const QString mode = app.arguments()[2];
        const int result = probe(mode);
        diagnostic(QString("probe completed mode=%1 exit=%2").arg(mode).arg(result));
        return result;
    }
    BeatQuayConfigIdentityTest test;
    return QTest::qExec(&test, argc, argv);
}
#include "BeatQuayConfigIdentityTest.moc"
