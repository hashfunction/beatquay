// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "ProjectExportFactsCollector.h"
#include "ProjectExportSession.h"
#include "Engine.h"
#include "Song.h"
#include "SampleTrack.h"
#include "SampleClip.h"
#include "DataFile.h"
#include <QFile>
#include <QTemporaryDir>
#include <QtTest>
#include <sndfile.h>
using namespace lmms;
class ProjectExportFactsCollectorTest : public QObject
{
	Q_OBJECT
private slots:
	void initTestCase() { Engine::init(true); }
	void cleanupTestCase() { Engine::destroy(); }
	void init() { Engine::getSong()->clearProject(); }
	void actualEmptySongIsBlocked()
	{
		QTemporaryDir directory;
		const auto facts = ProjectExportFactsCollector::collect(ProjectRenderer::ExportFileFormat::Wave,
			{directory.filePath("out.wav")}, false, false, 1);
		QCOMPARE(facts.outputs.size(), 1);
		QCOMPARE(facts.outputs[0].renderableTrackCount, 0);
		ProjectExportSession session(facts.outputs, facts.protectedPaths);
		QVERIFY(session.hasErrors());
	}
	void actualSampleResourceIsObservedWithoutSavingOrChangingIt()
	{
		QTemporaryDir directory;
		const auto source = directory.filePath(QString::fromUtf8("音符 source.wav"));
		QFile wave(source);
		QVERIFY(wave.open(QIODevice::WriteOnly | QIODevice::NewOnly));
		SF_INFO info{};
		info.channels = 2; info.samplerate = 44100; info.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
		auto* stream = sf_open_fd(wave.handle(), SFM_WRITE, &info, SF_FALSE);
		QVERIFY(stream);
		const short samples[] = {1000,1000,-1000,-1000,1000,1000,-1000,-1000};
		QCOMPARE(sf_writef_short(stream, samples, 4), 4);
		QCOMPARE(sf_close(stream), 0);
		wave.close();
		QVERIFY(wave.open(QIODevice::ReadOnly));
		const auto original = wave.readAll();
		wave.close();
		auto* track = new SampleTrack(Engine::getSong());
		auto* clip = dynamic_cast<SampleClip*>(track->createClip(TimePos(0)));
		QVERIFY(clip);
		clip->setSampleFile(source);
		clip->changeLength(TimePos(1,0));
		DataFile before(DataFile::Type::SongProject);
		Engine::getSong()->saveState(before, before.content());
		const auto facts = ProjectExportFactsCollector::collect(ProjectRenderer::ExportFileFormat::Wave,
			{directory.filePath("out.wav")}, false, false, 1);
		QCOMPARE(facts.outputs[0].renderableTrackCount, 1);
		QVERIFY(facts.outputs[0].encoderAvailable);
		QVERIFY(facts.outputs[0].timelineEndTick > facts.outputs[0].timelineStartTick);
		QCOMPARE(facts.outputs[0].resources.size(), 1);
		QCOMPARE(facts.outputs[0].resources[0].path, source);
		QVERIFY(facts.outputs[0].resources[0].exists && facts.outputs[0].resources[0].readable);
		QVERIFY(facts.protectedPaths.contains(source));
		DataFile after(DataFile::Type::SongProject);
		Engine::getSong()->saveState(after, after.content());
		QCOMPARE(after.toString(), before.toString());
		QVERIFY(wave.open(QIODevice::ReadOnly));
		QCOMPARE(wave.readAll(), original);
		wave.close();
		QVERIFY(QFile::rename(source, directory.filePath("retained.wav")));
		const auto missing = ProjectExportFactsCollector::collect(ProjectRenderer::ExportFileFormat::Wave,
			{directory.filePath("out.wav")}, false, false, 1);
		QVERIFY(!missing.outputs[0].resources[0].exists);
		ProjectExportSession session(missing.outputs, missing.protectedPaths);
		QVERIFY(session.hasErrors());
	}
};
QTEST_GUILESS_MAIN(ProjectExportFactsCollectorTest)
#include "ProjectExportFactsCollectorTest.moc"
