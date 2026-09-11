// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ProjectExportCheck.h"

#include <QtTest>
#include <algorithm>
#include <limits>

using namespace lmms;
using Code = ProjectExportIssue::Code;
using Severity = ProjectExportIssue::Severity;

class ProjectExportCheckTest : public QObject
{
	Q_OBJECT

	static ProjectExportFacts validFacts()
	{
		ProjectExportFacts facts;
		facts.renderableTrackCount = 1;
		facts.timelineEndTick = 192;
		facts.durationSeconds = 2.0;
		facts.encoderAvailable = true;
		facts.outputPath = QString::fromUtf8("/facts-only/音符 é.wav");
		facts.outputParentWritable = true;
		return facts;
	}

	static ProjectExportFacts completedFacts()
	{
		auto facts = validFacts();
		facts.renderCompleted = true;
		facts.outputExists = true;
		facts.outputIsRegularFile = true;
		facts.outputReadable = true;
		facts.outputSize = 4096;
		return facts;
	}

	static void expectIssue(const QList<ProjectExportIssue>& issues, Code code,
		Severity severity, const QString& path = {})
	{
		QCOMPARE(issues.size(), 1);
		QCOMPARE(issues.front().code, code);
		QCOMPARE(issues.front().severity, severity);
		QCOMPARE(issues.front().path, path);
		QVERIFY(!issues.front().message.isEmpty());
		QVERIFY(!issues.front().recoveryAction.isEmpty());
	}

private slots:
	void validProject_data()
	{
		QTest::addColumn<int>("format");
		QTest::newRow("wav") << static_cast<int>(ProjectRenderer::ExportFileFormat::Wave);
		QTest::newRow("flac") << static_cast<int>(ProjectRenderer::ExportFileFormat::Flac);
		QTest::newRow("ogg") << static_cast<int>(ProjectRenderer::ExportFileFormat::Ogg);
		QTest::newRow("mp3") << static_cast<int>(ProjectRenderer::ExportFileFormat::MP3);
	}

	void validProject()
	{
		QFETCH(int, format);
		auto facts = validFacts();
		facts.format = static_cast<ProjectRenderer::ExportFileFormat>(format);
		QVERIFY(ProjectExportCheck::beforeExport(facts).isEmpty());
	}

	void emptyProject_data()
	{
		QTest::addColumn<int>("tracks");
		QTest::newRow("none-renderable") << 0;
		QTest::newRow("invalid-count") << -1;
	}

	void emptyProject()
	{
		QFETCH(int, tracks);
		auto facts = validFacts();
		facts.renderableTrackCount = tracks;
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::EmptyProject, Severity::Error);
	}

	void knownSilenceIsAWarning()
	{
		auto facts = validFacts();
		facts.knownSilent = true;
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::SilentProject, Severity::Warning);
	}

	void missingUnicodeResource()
	{
		auto facts = validFacts();
		const auto path = QString::fromUtf8("C:/楽器/音符 é.wav");
		facts.resources.append({path, false, false});
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::MissingResource, Severity::Error, path);
	}

	void unreadableResource()
	{
		auto facts = validFacts();
		facts.resources.append({"C:/samples/read-only.wav", true, false});
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::UnreadableResource,
			Severity::Error, facts.resources.front().path);
	}

	void unavailableEncoder_data()
	{
		QTest::addColumn<int>("format");
		QTest::addColumn<bool>("available");
		QTest::newRow("mp3-disabled") << static_cast<int>(ProjectRenderer::ExportFileFormat::MP3) << false;
		QTest::newRow("sentinel") << static_cast<int>(ProjectRenderer::ExportFileFormat::Count) << true;
		QTest::newRow("negative") << -1 << true;
		QTest::newRow("out-of-range") << 99 << true;
	}

	void unavailableEncoder()
	{
		QFETCH(int, format);
		QFETCH(bool, available);
		auto facts = validFacts();
		facts.format = static_cast<ProjectRenderer::ExportFileFormat>(format);
		facts.encoderAvailable = available;
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::EncoderUnavailable, Severity::Error);
	}

	void invalidTimeline_data()
	{
		QTest::addColumn<qint64>("start");
		QTest::addColumn<qint64>("end");
		QTest::addColumn<double>("duration");
		QTest::newRow("negative-start") << qint64(-1) << qint64(192) << 2.0;
		QTest::newRow("empty-range") << qint64(0) << qint64(0) << 2.0;
		QTest::newRow("reversed-range") << qint64(192) << qint64(1) << 2.0;
		QTest::newRow("zero-duration") << qint64(0) << qint64(192) << 0.0;
		QTest::newRow("negative-duration") << qint64(0) << qint64(192) << -2.0;
		QTest::newRow("nan-duration") << qint64(0) << qint64(192) << std::numeric_limits<double>::quiet_NaN();
		QTest::newRow("infinite-duration") << qint64(0) << qint64(192) << std::numeric_limits<double>::infinity();
	}

	void invalidTimeline()
	{
		QFETCH(qint64, start);
		QFETCH(qint64, end);
		QFETCH(double, duration);
		auto facts = validFacts();
		facts.timelineStartTick = start;
		facts.timelineEndTick = end;
		facts.durationSeconds = duration;
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::InvalidTimeline, Severity::Error);
	}

	void existingDestinationWarningDoesNotAuthorizeReplacement()
	{
		auto facts = validFacts();
		facts.outputExists = facts.outputIsRegularFile = facts.outputWritable = true;
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::ExistingDestination,
			Severity::Warning, facts.outputPath);
	}

	void unwritableParent()
	{
		auto facts = validFacts();
		facts.outputParentWritable = false;
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::OutputParentNotWritable,
			Severity::Error, facts.outputPath);
	}

	void missingOutputPath()
	{
		auto facts = validFacts();
		facts.outputPath.clear();
		facts.outputParentWritable = false;
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::MissingOutputPath, Severity::Error);
	}

	void existingDestinationMustBeRegularAndWritable()
	{
		auto facts = validFacts();
		facts.outputExists = true;
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::OutputNotRegular,
			Severity::Error, facts.outputPath);
		facts.outputIsRegularFile = true;
		expectIssue(ProjectExportCheck::beforeExport(facts), Code::OutputNotWritable,
			Severity::Error, facts.outputPath);
	}

	void incompleteRenderCannotAcceptAnExistingNonemptyFile()
	{
		auto facts = completedFacts();
		facts.renderCompleted = false;
		expectIssue(ProjectExportCheck::afterExport(facts), Code::RenderNotCompleted,
			Severity::Error, facts.outputPath);
	}

	void completedOutputMustExistAndBeReadable()
	{
		auto facts = completedFacts();
		facts.outputExists = false;
		expectIssue(ProjectExportCheck::afterExport(facts), Code::MissingOutput, Severity::Error, facts.outputPath);
		facts.outputExists = true;
		facts.outputIsRegularFile = false;
		expectIssue(ProjectExportCheck::afterExport(facts), Code::OutputNotRegular, Severity::Error, facts.outputPath);
		facts.outputIsRegularFile = true;
		facts.outputReadable = false;
		expectIssue(ProjectExportCheck::afterExport(facts), Code::OutputUnreadable, Severity::Error, facts.outputPath);
		facts.outputReadable = true;
		facts.outputPath.clear();
		expectIssue(ProjectExportCheck::afterExport(facts), Code::MissingOutputPath, Severity::Error);
	}

	void emptyCompletedOutput_data()
	{
		QTest::addColumn<qint64>("bytes");
		QTest::newRow("zero") << qint64(0);
		QTest::newRow("invalid-size") << qint64(-1);
	}

	void emptyCompletedOutput()
	{
		QFETCH(qint64, bytes);
		auto facts = completedFacts();
		facts.outputSize = bytes;
		expectIssue(ProjectExportCheck::afterExport(facts), Code::EmptyOutput, Severity::Error, facts.outputPath);
	}

	void nonemptyCompletedOutput()
	{
		auto facts = completedFacts();
		facts.outputSize = 1;
		// The postcheck is about the observed output, not a second project scan.
		facts.renderableTrackCount = 0;
		facts.outputParentWritable = false;
		QVERIFY(ProjectExportCheck::afterExport(facts).isEmpty());
	}

	void factsAreNotMutatedOrReplacedByFilesystemGuesses()
	{
		auto facts = validFacts();
		facts.resources.append({"facts-only:/missing-on-this-host/音符.wav", true, true});
		const auto original = facts;
		QVERIFY(ProjectExportCheck::beforeExport(facts).isEmpty());
		QVERIFY(facts == original);
	}

	void deterministicIssueOrderingAndDuplicateResources()
	{
		auto facts = validFacts();
		facts.encoderAvailable = false;
		facts.timelineEndTick = 0;
		facts.knownSilent = true;
		facts.outputExists = facts.outputIsRegularFile = facts.outputWritable = true;
		facts.resources = {{"z.wav", false, false}, {"a.wav", false, false},
			{"read.wav", true, false}, {"a.wav", false, false}};
		const auto issues = ProjectExportCheck::beforeExport(facts);
		QCOMPARE(issues.size(), 7);
		const QList<Code> expected{Code::EncoderUnavailable, Code::InvalidTimeline,
			Code::MissingResource, Code::MissingResource, Code::UnreadableResource,
			Code::ExistingDestination, Code::SilentProject};
		for (qsizetype i = 0; i < issues.size(); ++i)
		{
			QCOMPARE(issues[i].code, expected[i]);
			QCOMPARE(issues[i].severity, i < 5 ? Severity::Error : Severity::Warning);
		}
		QCOMPARE(issues[2].path, QString("a.wav"));
		QCOMPARE(issues[3].path, QString("z.wav"));
		std::reverse(facts.resources.begin(), facts.resources.end());
		QVERIFY(ProjectExportCheck::beforeExport(facts) == issues);
	}
};

QTEST_GUILESS_MAIN(ProjectExportCheckTest)
#include "ProjectExportCheckTest.moc"
