// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include <QtTest>
#include <QTemporaryDir>

#include "AudioEngine.h"
#include "Engine.h"
#include "RenderManager.h"
#include "SampleTrack.h"
#include "Song.h"

#include <sndfile.h>

using namespace lmms;

class RenderManagerLifecycleTest : public QObject
{
	Q_OBJECT
	static OutputSettings settings()
	{
		return {44100, 160, OutputSettings::BitDepth::Depth16Bit, OutputSettings::StereoMode::Stereo};
	}

	static bool readableFinalizedWave(const QString& path)
	{
		QFile file(path);
		if (!file.open(QIODevice::ReadOnly)) { return false; }
		SF_INFO info{};
		auto* stream = sf_open_fd(file.handle(), SFM_READ, &info, SF_FALSE);
		if (!stream) { return false; }
		const bool valid = info.frames > 0 && info.channels == 2 && info.samplerate == 44100
			&& (info.format & SF_FORMAT_TYPEMASK) == SF_FORMAT_WAV;
		return sf_close(stream) == 0 && valid;
	}

private slots:
	void initTestCase() { Engine::init(true); }
	void cleanupTestCase() { Engine::destroy(); }
	void init() { Engine::getSong()->clearProject(); }

	void completionFinalizesAndRestoresBeforeNotification()
	{
		QTemporaryDir directory;
		QVERIFY(directory.isValid());
		new SampleTrack(Engine::getSong()); // No external samples or instruments.
		const auto path = directory.filePath(QString::fromUtf8("音符 é.wav"));
		auto* originalDevice = Engine::audioEngine()->audioDev();
		RenderManager manager(settings(), ProjectRenderer::ExportFileFormat::Wave, path);
		QSignalSpy finished(&manager, &RenderManager::finished);
		bool restoredAtNotification = false;
		bool readableAtNotification = false;
		connect(&manager, &RenderManager::finished, this, [&]
		{
			restoredAtNotification = Engine::audioEngine()->audioDev() == originalDevice;
			readableAtNotification = readableFinalizedWave(path);
		});
		manager.renderProject();
		QTRY_COMPARE_WITH_TIMEOUT(finished.size(), 1, 30000);
		QVERIFY(restoredAtNotification);
		QVERIFY(readableAtNotification);
	}

	void cancellationClosesBeforeRemovingOnlyItsPartialOutput()
	{
		QTemporaryDir directory;
		QVERIFY(directory.isValid());
		new SampleTrack(Engine::getSong());
		const auto path = directory.filePath(QString::fromUtf8("cancel 音符.wav"));
		QFile unrelated(directory.filePath("keep.wav"));
		QVERIFY(unrelated.open(QIODevice::WriteOnly | QIODevice::NewOnly));
		QCOMPARE(unrelated.write("keep"), 4);
		unrelated.close();
		auto* originalDevice = Engine::audioEngine()->audioDev();
		RenderManager manager(settings(), ProjectRenderer::ExportFileFormat::Wave, path);
		manager.renderProject();
		manager.abortProcessing();
		QVERIFY(!QFileInfo::exists(path));
		QVERIFY(Engine::audioEngine()->audioDev() == originalDevice);
		QVERIFY(unrelated.open(QIODevice::ReadOnly));
		QCOMPARE(unrelated.readAll(), QByteArray("keep"));
	}

	void multitrackRestoresMutesAndFinalizesEveryDestination()
	{
		QTemporaryDir directory;
		QVERIFY(directory.isValid());
		auto* first = new SampleTrack(Engine::getSong());
		auto* second = new SampleTrack(Engine::getSong());
		auto* muted = new SampleTrack(Engine::getSong());
		first->setName(QString::fromUtf8("音符"));
		second->setName(QString::fromUtf8("音符"));
		muted->setMuted(true);
		auto* originalDevice = Engine::audioEngine()->audioDev();
		RenderManager manager(settings(), ProjectRenderer::ExportFileFormat::Wave, directory.path());
		QSignalSpy finished(&manager, &RenderManager::finished);
		manager.renderTracks();
		QTRY_COMPARE_WITH_TIMEOUT(finished.size(), 1, 30000);
		QVERIFY(!first->isMuted());
		QVERIFY(!second->isMuted());
		QVERIFY(muted->isMuted());
		QVERIFY(Engine::audioEngine()->audioDev() == originalDevice);
		QVERIFY(readableFinalizedWave(directory.filePath(QString::fromUtf8("1_音符.wav"))));
		QVERIFY(readableFinalizedWave(directory.filePath(QString::fromUtf8("2_音符.wav"))));
		QCOMPARE(QDir(directory.path()).entryList(QDir::Files).size(), 2);
	}
};

QTEST_GUILESS_MAIN(RenderManagerLifecycleTest)
#include "RenderManagerLifecycleTest.moc"
