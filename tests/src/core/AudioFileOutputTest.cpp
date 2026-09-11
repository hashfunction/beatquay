// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "AudioFileOutput.h"
#include <QtTest>
#include <QTemporaryDir>

using namespace lmms;

class AudioFileOutputTest : public QObject
{
	Q_OBJECT
private slots:
	void finalizeOnceWhileOpenThenClose()
	{
		QTemporaryDir directory;
		QVERIFY(directory.isValid());
		const auto path = directory.filePath(QString::fromUtf8("音符 é.wav"));
		AudioFileOutput output(path);
		QVERIFY(output.open());
		QCOMPARE(output.write("header", 6), 6);
		int closes = 0;
		const auto closeEncoder = [&]
		{
			++closes;
			return output.isOpen() && output.write("footer", 6) == 6;
		};
		QVERIFY(output.finalize(closeEncoder));
		QVERIFY(!output.isOpen());
		QVERIFY(output.finalize(closeEncoder));
		QCOMPARE(closes, 1);
		QFile read(path);
		QVERIFY(read.open(QIODevice::ReadOnly));
		QCOMPARE(read.readAll(), QByteArray("headerfooter"));
	}

	void exclusiveOpenRefusesAnExistingFileWithoutTruncation()
	{
		QTemporaryDir directory;
		const auto path = directory.filePath("source.wav");
		QFile keep(path);
		QVERIFY(keep.open(QIODevice::WriteOnly | QIODevice::NewOnly));
		QCOMPARE(keep.write("source"), 6);
		keep.close();
		AudioFileOutput output(path);
		QVERIFY2(!output.open(true), "A GUI staging file must be created exclusively");
		QVERIFY(!output.removePartial());
		QVERIFY(keep.open(QIODevice::ReadOnly));
		QCOMPARE(keep.readAll(), QByteArray("source"));
	}

	void encoderFailureStillClosesAndRemainsFailed()
	{
		QTemporaryDir directory;
		AudioFileOutput output(directory.filePath("failed.wav"));
		QVERIFY(output.open());
		int calls = 0;
		QVERIFY(!output.finalize([&] { ++calls; return false; }));
		QVERIFY(!output.isOpen());
		QVERIFY(!output.finalize([&] { ++calls; return true; }));
		QCOMPARE(calls, 1);
	}

	void writeFailureCannotBecomeSuccessfulOnClose()
	{
		QTemporaryDir directory;
		AudioFileOutput output(directory.filePath("failed.wav"));
		QVERIFY(output.open());
		output.recordWriteFailure(); // The encoder reported a short/failed write.
		QVERIFY(output.hasWriteFailure());
		QVERIFY(!output.finalize([] { return true; }));
		QVERIFY(!output.isOpen());
	}

	void failedOpenAndWriteReturnFailure()
	{
		QTemporaryDir directory;
		AudioFileOutput output(directory.filePath("absent/output.wav"));
		QVERIFY(!output.open());
		QCOMPARE(output.write("x", 1), -1);
		QVERIFY(output.hasWriteFailure());
		QVERIFY(!output.finalize([] { return true; }));
	}

	void cancellationRequiresFinalizationAndPreservesOtherFiles()
	{
		QTemporaryDir directory;
		QFile keep(directory.filePath("keep.wav"));
		QVERIFY(keep.open(QIODevice::WriteOnly | QIODevice::NewOnly));
		QCOMPARE(keep.write("keep"), 4);
		keep.close();
		const auto path = directory.filePath("partial.wav");
		AudioFileOutput output(path);
		QVERIFY(output.open());
		QVERIFY(!output.removePartial());
		QVERIFY(QFileInfo::exists(path));
		QVERIFY(output.finalize([] { return true; }));
		QVERIFY(output.removePartial());
		QVERIFY(!QFileInfo::exists(path));
		QVERIFY(keep.open(QIODevice::ReadOnly));
		QCOMPARE(keep.readAll(), QByteArray("keep"));
	}

	void neverOpenedDestinationIsNotOwnedForRemoval()
	{
		QTemporaryDir directory;
		const auto path = directory.filePath("existing.wav");
		QFile keep(path);
		QVERIFY(keep.open(QIODevice::WriteOnly | QIODevice::NewOnly));
		QCOMPARE(keep.write("keep"), 4);
		keep.close();
		AudioFileOutput output(path);
		QVERIFY(!output.finalize([] { return true; }));
		QVERIFY(!output.removePartial());
		QVERIFY(keep.open(QIODevice::ReadOnly));
		QCOMPARE(keep.readAll(), QByteArray("keep"));
	}

	void cancelledReplacementIsPreserved_data()
	{
		QTest::addColumn<QByteArray>("replacement");
		QTest::newRow("different-content") << QByteArray("other");
		QTest::newRow("identical-content-new-identity") << QByteArray("owned");
	}

	void cancelledReplacementIsPreserved()
	{
		QFETCH(QByteArray, replacement);
		QTemporaryDir directory;
		const auto path = directory.filePath("partial.wav");
		const auto retained = directory.filePath("retained.wav");
		AudioFileOutput output(path);
		QVERIFY(output.open());
		QCOMPARE(output.write("owned", 5), 5);
		QVERIFY(output.finalize([] { return true; }));
		QVERIFY(QFile::rename(path, retained));
		QFile foreign(path);
		QVERIFY(foreign.open(QIODevice::WriteOnly | QIODevice::NewOnly));
		QCOMPARE(foreign.write(replacement), replacement.size());
		foreign.close();
		QVERIFY2(!output.removePartial(), "Cancellation must not remove a substituted regular file");
		QVERIFY(foreign.open(QIODevice::ReadOnly));
		QCOMPARE(foreign.readAll(), replacement);
		QFile original(retained);
		QVERIFY(original.open(QIODevice::ReadOnly));
		QCOMPARE(original.readAll(), QByteArray("owned"));
	}

	void failedRemovalReportsFailureWithoutDeletingADirectory()
	{
		QTemporaryDir directory;
		const auto path = directory.filePath("partial.wav");
		AudioFileOutput output(path);
		QVERIFY(output.open());
		QVERIFY(output.finalize([] { return true; }));
		QVERIFY(QFile::rename(path, directory.filePath("retained.wav")));
		QVERIFY(QDir().mkdir(path));
		QVERIFY(!output.removePartial());
		QVERIFY(QFileInfo(path).isDir());
		QVERIFY(QFileInfo::exists(directory.filePath("retained.wav")));
	}
};

QTEST_GUILESS_MAIN(AudioFileOutputTest)
#include "AudioFileOutputTest.moc"
