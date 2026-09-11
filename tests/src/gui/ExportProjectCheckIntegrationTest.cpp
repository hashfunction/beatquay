// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ProjectExportSession.h"
#include <QFile>
#include <QTemporaryDir>
#include <QtTest>
using namespace lmms;
class ExportProjectCheckIntegrationTest : public QObject
{
	Q_OBJECT
	static ProjectExportFacts facts(const QString& path)
	{
		ProjectExportFacts value;
		value.renderableTrackCount = 1;
		value.timelineEndTick = 192;
		value.durationSeconds = 2;
		value.encoderAvailable = true;
		value.outputParentWritable = true;
		value.outputPath = path;
		return value;
	}
	static bool write(const QString& path, const QByteArray& bytes)
	{
		QFile file(path);
		return file.open(QIODevice::WriteOnly | QIODevice::NewOnly) && file.write(bytes) == bytes.size();
	}
	static RenderResult completed(const QString& path)
	{
		RenderOutputResult output;
		output.path = path;
		output.status = RenderStatus::Succeeded;
		output.encoderFinalized = true;
		return {RenderStatus::Succeeded, {output}, {}};
	}
private slots:
	void blockingErrorConstructsNoRenderer()
	{
		QTemporaryDir dir;
		auto invalid = facts(dir.filePath("out.wav"));
		invalid.resources = {{dir.filePath("missing-sample.wav"), false, false}};
		ProjectExportSession session({invalid});
		int calls = 0;
		QVERIFY(session.hasErrors());
		QVERIFY(!session.start(ProjectExportSession::Decision::Continue, [&](const auto&, const auto&) { ++calls; }));
		QCOMPARE(calls, 0);
	}
	void warningContinueStartsExactlyOnce()
	{
		QTemporaryDir dir;
		auto warning = facts(dir.filePath("out.wav"));
		warning.knownSilent = true;
		ProjectExportSession session({warning});
		int calls = 0;
		QString actualPath;
		QVERIFY(!session.hasErrors());
		QVERIFY(!session.issues().isEmpty());
		const auto renderer = [&](const auto& targets, const auto&)
		{
			++calls;
			QCOMPARE(targets.size(), 1);
			actualPath = targets[0].path;
		};
		QVERIFY(session.start(ProjectExportSession::Decision::Continue, renderer));
		QVERIFY(!session.start(ProjectExportSession::Decision::Continue, renderer));
		QCOMPARE(calls, 1);
		QCOMPARE(actualPath, warning.outputPath);
	}
	void warningCancelConstructsNoRenderer()
	{
		QTemporaryDir dir;
		auto warning = facts(dir.filePath("out.wav"));
		warning.knownSilent = true;
		ProjectExportSession session({warning});
		int calls = 0;
		QVERIFY(!session.start(ProjectExportSession::Decision::Cancel, [&](const auto&, const auto&) { ++calls; }));
		QVERIFY(!session.start(ProjectExportSession::Decision::Continue, [&](const auto&, const auto&) { ++calls; }));
		QCOMPARE(calls, 0);
	}
	void lateTargetAfterWarningPreventsConstruction()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("out.wav");
		ProjectExportSession session({facts(path)});
		QVERIFY(write(path, "late"));
		int calls = 0;
		QVERIFY(!session.start(ProjectExportSession::Decision::Continue, [&](const auto&, const auto&) { ++calls; }));
		QCOMPARE(calls, 0);
		QVERIFY(session.hasErrors());
	}
	void resourceRemovedDuringWarningPreventsConstruction()
	{
		QTemporaryDir dir;
		const auto resource = dir.filePath("sample.wav");
		QVERIFY(write(resource, "sample"));
		auto warning = facts(dir.filePath("out.wav"));
		warning.knownSilent = true;
		warning.resources = {{resource, true, true}};
		ProjectExportSession session({warning}, {resource});
		QVERIFY(!session.hasErrors());
		QVERIFY(QFile::remove(resource));
		int calls = 0;
		QVERIFY(!session.start(ProjectExportSession::Decision::Continue, [&](const auto&, const auto&) { ++calls; }));
		QCOMPARE(calls, 0);
		QVERIFY(session.hasErrors());
	}

	void zeroByteCompletionFails()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("empty.wav");
		ProjectExportSession session({facts(path)});
		QVERIFY(session.start(ProjectExportSession::Decision::Continue, [&](const auto&, const auto&) {}));
		QVERIFY(write(path, {}));
		auto result = completed(path);
		const auto issues = session.postflight(result);
		QVERIFY(!issues.isEmpty());
		QCOMPARE(result.status, RenderStatus::Failed);
		QCOMPARE(issues[0].code, ProjectExportIssue::Code::EmptyOutput);
	}
	void successfulOutputReportsExactPathAndBytes()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath(QString::fromUtf8("音符 é.wav"));
		ProjectExportSession session({facts(path)});
		QVERIFY(session.start(ProjectExportSession::Decision::Continue, [&](const auto&, const auto&) {}));
		QVERIFY(write(path, "rendered"));
		auto result = completed(path);
		QVERIFY(session.postflight(result).isEmpty());
		QCOMPARE(result.status, RenderStatus::Succeeded);
		QCOMPARE(result.outputs[0].path, path);
		QCOMPARE(result.outputs[0].bytes, 8);
	}
	void workerFinishedWithoutEncoderFinalizationFails()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("out.wav");
		ProjectExportSession session({facts(path)});
		QVERIFY(session.start(ProjectExportSession::Decision::Continue, [&](const auto&, const auto&) {}));
		QVERIFY(write(path, "unfinished"));
		auto result = completed(path);
		result.outputs[0].encoderFinalized = false;
		QVERIFY(!session.postflight(result).isEmpty());
		QCOMPARE(result.status, RenderStatus::Failed);
	}
	void missingAndUnexpectedBatchOutputsCannotSucceed()
	{
		QTemporaryDir dir;
		const auto first = dir.filePath("1_first.wav");
		const auto second = dir.filePath("2_second.wav");
		ProjectExportSession session({facts(first), facts(second)});
		QVERIFY(session.start(ProjectExportSession::Decision::Continue, [&](const auto&, const auto&) {}));
		QVERIFY(write(first, "rendered"));
		auto missing = completed(first);
		QVERIFY(!session.postflight(missing).isEmpty());
		QCOMPARE(missing.status, RenderStatus::Failed);
		const auto unknown = dir.filePath("unknown.wav");
		QVERIFY(write(unknown, "foreign"));
		auto unexpected = completed(unknown);
		QVERIFY(!session.postflight(unexpected).isEmpty());
		QCOMPARE(unexpected.status, RenderStatus::Failed);
	}
	void failedTypedResultCannotBecomeSuccess()
	{
		QTemporaryDir dir;
		const auto path = dir.filePath("out.wav");
		ProjectExportSession session({facts(path)});
		QVERIFY(session.start(ProjectExportSession::Decision::Continue, [&](const auto&, const auto&) {}));
		QVERIFY(write(path, "old"));
		auto result = completed(path);
		result.status = RenderStatus::Failed;
		result.outputs[0].status = RenderStatus::Failed;
		result.outputs[0].error = "encoder failure";
		QVERIFY(!session.postflight(result).isEmpty());
		QCOMPARE(result.status, RenderStatus::Failed);
	}
};
QTEST_GUILESS_MAIN(ExportProjectCheckIntegrationTest)
#include "ExportProjectCheckIntegrationTest.moc"
