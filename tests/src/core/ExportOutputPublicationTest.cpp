// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ExportOutputPublication.h"
#include <QFile>
#include <QFileInfo>
#include <QTemporaryDir>
#include <QtTest>
#ifdef Q_OS_WIN
#include <windows.h>
#else
#include <unistd.h>
#endif
using namespace lmms;
namespace
{
bool write(const QString& path, const QByteArray& bytes)
{
	QFile file(path);
	return file.open(QIODevice::WriteOnly | QIODevice::NewOnly) && file.write(bytes) == bytes.size();
}
QByteArray read(const QString& path)
{
	QFile file(path);
	return file.open(QIODevice::ReadOnly) ? file.readAll() : QByteArray{};
}
bool prepare(ExportOutputPublication& output)
{
	QString error;
	if (!output.prepare(error) || !write(output.stagingPath(), "rendered")) { return false; }
	const auto identity = exportFileIdentity(output.stagingPath());
	if (!identity) { return false; }
	output.claimOutput(*identity);
	return true;
}
}
class ExportOutputPublicationTest : public QObject
{
	Q_OBJECT
private slots:
	void newOutputRemainsAbsentUntilPublication()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath(QString::fromUtf8("音符 é.wav"));
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot);
		QVERIFY(prepare(output));
		QVERIFY(!QFileInfo::exists(path));
		const auto result = output.publish();
		QVERIFY2(result.published, qPrintable(result.error));
		QCOMPARE(result.path, path);
		QCOMPARE(result.bytes, 8);
		QCOMPARE(read(path), QByteArray("rendered"));
		QVERIFY(!QFileInfo::exists(output.stagingPath()));
	}
	void approvedReplacementRetainsOriginal()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("existing.wav");
		QVERIFY(write(path, "original"));
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot);
		QVERIFY(prepare(output));
		QCOMPARE(read(path), QByteArray("original"));
		const auto result = output.publish();
		QVERIFY2(result.published, qPrintable(result.error));
		QCOMPARE(read(path), QByteArray("rendered"));
		QCOMPARE(read(result.previousOutputPath), QByteArray("original"));
	}
	void changedDestinationSinceConsent_data()
	{
		QTest::addColumn<bool>("sameBytes");
		QTest::newRow("different-content") << false;
		QTest::newRow("same-content-new-identity") << true;
	}
	void changedDestinationSinceConsent()
	{
		QFETCH(bool, sameBytes);
		QTemporaryDir dir;
		const auto path = dir.filePath("existing.wav");
		QVERIFY(write(path, "original"));
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot);
		QVERIFY(prepare(output));
		QVERIFY(QFile::rename(path, dir.filePath("saved-original")));
		const auto foreign = sameBytes ? QByteArray("original") : QByteArray("replaced");
		QVERIFY(write(path, foreign));
		const auto result = output.publish();
		QVERIFY(!result.published);
		QVERIFY(!result.error.isEmpty());
		QCOMPARE(read(path), foreign);
		QCOMPARE(read(dir.filePath("saved-original")), QByteArray("original"));
	}
	void lateDestinationIsNeverOverwritten()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("new.wav");
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot, {}, [&](auto checkpoint)
		{
			if (checkpoint == ExportOutputPublication::Checkpoint::BeforePublish) { QVERIFY(write(path, "late")); }
		});
		QVERIFY(prepare(output));
		const auto result = output.publish();
		QVERIFY(!result.published);
		QCOMPARE(read(path), QByteArray("late"));
		QCOMPARE(read(result.retainedPartialPath), QByteArray("rendered"));
	}
	void cancellationPreservesSubstitutedStageAndUnknownEntries()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("new.wav");
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		QString foreignPath;
		QString extra;
		{
			ExportOutputPublication output(*snapshot);
			QVERIFY(prepare(output));
			foreignPath = output.stagingPath();
			extra = QFileInfo(foreignPath).dir().filePath("keep-project.mmp");
			QVERIFY(write(extra, "project"));
			QVERIFY(QFile::rename(foreignPath, dir.filePath("saved-render")));
			QVERIFY(write(foreignPath, "foreign"));
			QString retained;
			QVERIFY(!output.discard(retained));
			QCOMPARE(retained, foreignPath);
		}
		QCOMPARE(read(foreignPath), QByteArray("foreign"));
		QCOMPARE(read(extra), QByteArray("project"));
		QCOMPARE(read(dir.filePath("saved-render")), QByteArray("rendered"));
		QVERIFY(!QFileInfo::exists(path));
	}
	void successfulPublicationDisclosesUnknownStagingResidue()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("new.wav");
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot);
		QVERIFY(prepare(output));
		const auto stageDirectory = QFileInfo(output.stagingPath()).absolutePath();
		const auto foreign = QDir(stageDirectory).filePath("unknown.mmp");
		QVERIFY(write(foreign, "project"));
		const auto result = output.publish();
		QVERIFY(result.published);
		QCOMPARE(result.retainedPartialPath, stageDirectory);
		QCOMPARE(read(foreign), QByteArray("project"));
		QCOMPARE(read(path), QByteArray("rendered"));
	}

	void emptyOutputCannotPublish()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("new.wav");
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot);
		QVERIFY(output.prepare(error));
		QVERIFY(write(output.stagingPath(), {}));
		output.claimOutput(*exportFileIdentity(output.stagingPath()));
		QVERIFY(!output.publish().published);
		QVERIFY(!QFileInfo::exists(path));
	}
	void projectOrResourceCannotBeDestination()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("source.wav");
		QVERIFY(write(path, "source"));
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot, {path});
		QVERIFY(!output.prepare(error));
		QCOMPARE(read(path), QByteArray("source"));
	}
	void protectedHardLinkResourceTargetsTheSameFile()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("source.wav");
		const auto resource = dir.filePath("resource-hard-link.wav");
		QVERIFY(write(path, "source"));
#ifdef Q_OS_WIN
		QVERIFY(CreateHardLinkW(reinterpret_cast<LPCWSTR>(resource.utf16()), reinterpret_cast<LPCWSTR>(path.utf16()), nullptr));
#else
		QCOMPARE(::link(QFile::encodeName(path).constData(), QFile::encodeName(resource).constData()), 0);
#endif
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot, {resource});
		QVERIFY(!output.prepare(error));
		QCOMPARE(read(path), QByteArray("source"));
		QCOMPARE(read(resource), QByteArray("source"));
	}

	void protectedSymlinkResourceTargetsTheSameFile()
	{
#ifdef Q_OS_WIN
		QSKIP("Windows shortcut creation is not a filesystem symlink; native hard-link coverage is separate.");
#else
		QTemporaryDir dir;
		const auto path = dir.filePath("source.wav");
		const auto resource = dir.filePath("resource-link.wav");
		QVERIFY(write(path, "source"));
		QVERIFY(QFile::link(path, resource));
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot, {resource});
		QVERIFY2(!output.prepare(error), "A resource symlink cannot authorize replacing its actual audio file");
		QCOMPARE(read(path), QByteArray("source"));
#endif
	}

	void editedContentsWithoutReplacementInvalidateConsent()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("existing.wav");
		QVERIFY(write(path, "original"));
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot);
		QVERIFY(prepare(output));
		QFile edited(path);
		QVERIFY(edited.open(QIODevice::WriteOnly));
		QCOMPARE(edited.write("replaced"), 8);
		edited.close();
		QCOMPARE(exportFileIdentity(path), snapshot->identity);
		QVERIFY(!output.publish().published);
		QCOMPARE(read(path), QByteArray("replaced"));
	}

	void displaceRacePreservesTheFileActuallyMoved()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("existing.wav");
		QVERIFY(write(path, "original"));
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot, {}, [&](auto checkpoint)
		{
			if (checkpoint != ExportOutputPublication::Checkpoint::BeforeDisplace) { return; }
			QVERIFY(QFile::rename(path, dir.filePath("saved-original")));
			QVERIFY(write(path, "foreign"));
		});
		QVERIFY(prepare(output));
		const auto result = output.publish();
		QVERIFY(!result.published);
		QCOMPARE(read(path), QByteArray("foreign"));
		QCOMPARE(read(dir.filePath("saved-original")), QByteArray("original"));
	}
	void conflictAfterDisplacementKeepsPriorAndRenderedBytes()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("existing.wav");
		QVERIFY(write(path, "original"));
		QString error;
		const auto snapshot = ExportDestinationSnapshot::capture(path, error);
		QVERIFY(snapshot);
		ExportOutputPublication output(*snapshot, {}, [&](auto checkpoint)
		{
			if (checkpoint == ExportOutputPublication::Checkpoint::AfterDisplace) { QVERIFY(write(path, "late")); }
		});
		QVERIFY(prepare(output));
		const auto result = output.publish();
		QVERIFY(!result.published);
		QCOMPARE(read(path), QByteArray("late"));
		QCOMPARE(read(result.previousOutputPath), QByteArray("original"));
		QCOMPARE(read(result.retainedPartialPath), QByteArray("rendered"));
	}
};
QTEST_GUILESS_MAIN(ExportOutputPublicationTest)
#include "ExportOutputPublicationTest.moc"
