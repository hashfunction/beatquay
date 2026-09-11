// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include <QtTest>
#include <QTemporaryDir>
#include <QPointer>

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

	static bool readableFinalizedAudio(const QString& path, int expectedType)
	{
		QFile file(path);
		if (!file.open(QIODevice::ReadOnly)) { return false; }
		SF_INFO info{};
		auto* stream = sf_open_fd(file.handle(), SFM_READ, &info, SF_FALSE);
		if (!stream) { return false; }
		const bool valid = info.frames > 0 && info.channels == 2 && info.samplerate == 44100
			&& (info.format & SF_FORMAT_TYPEMASK) == expectedType;
		short samples[2]{};
		const bool decoded = sf_readf_short(stream, samples, 1) == 1;
		return sf_close(stream) == 0 && valid && decoded;
	}
	static bool readableFinalizedWave(const QString& path) { return readableFinalizedAudio(path, SF_FORMAT_WAV); }

private slots:
	void initTestCase() { Engine::init(true); }
	void cleanupTestCase() { Engine::destroy(); }
	void init()
	{
		Engine::getSong()->clearProject();
		Engine::getSong()->setExportLoop(false);
		Engine::getSong()->setRenderBetweenMarkers(false);
		Engine::getSong()->setLoopRenderCount(1);
	}

	void completionFinalizesAndRestoresBeforeNotification()
	{
		QTemporaryDir directory;
		QVERIFY(directory.isValid());
		new SampleTrack(Engine::getSong()); // No external samples or instruments.
		const auto path = directory.filePath(QString::fromUtf8("音符 é.wav"));
		auto* originalDevice = Engine::audioEngine()->audioDev();
		RenderManager manager(settings(), ProjectRenderer::ExportFileFormat::Wave, path);
		QSignalSpy finished(&manager, &RenderManager::finished);
		QSignalSpy completed(&manager, &RenderManager::completed);
		bool restoredAtNotification = false;
		bool readableAtNotification = false;
		connect(&manager, &RenderManager::completed, this, [&](const RenderResult& result)
		{
			restoredAtNotification = Engine::audioEngine()->audioDev() == originalDevice;
			readableAtNotification = result.status == RenderStatus::Succeeded && readableFinalizedWave(path);
		});
		manager.renderProject();
		QTRY_COMPARE_WITH_TIMEOUT(finished.size(), 1, 30000);
		QVERIFY(restoredAtNotification);
		QVERIFY(readableAtNotification);
		QCOMPARE(completed.size(), 1);
		QCOMPARE(manager.result().status, RenderStatus::Succeeded);
		QCOMPARE(manager.result().outputs.size(), 1);
		QVERIFY(manager.result().outputs.front().encoderFinalized);
		QCOMPARE(manager.result().outputs.front().path, path);
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
		QSignalSpy completed(&manager, &RenderManager::completed);
		QSignalSpy finished(&manager, &RenderManager::finished);
		manager.renderProject();
		manager.abortProcessing();
		QVERIFY(!QFileInfo::exists(path));
		QVERIFY(Engine::audioEngine()->audioDev() == originalDevice);
		QVERIFY(unrelated.open(QIODevice::ReadOnly));
		QCOMPARE(unrelated.readAll(), QByteArray("keep"));
		QCOMPARE(completed.size(), 1);
		QCOMPARE(finished.size(), 0); // Preserve the old cancellation finish contract.
		QCOMPARE(manager.result().status, RenderStatus::Cancelled);
		QCOMPARE(manager.result().outputs.size(), 1);
		QVERIFY(manager.result().outputs.front().partialOutputRemoved);
		manager.abortProcessing();
		manager.renderProject();
		QVERIFY(QMetaObject::invokeMethod(&manager, "renderNextTrack", Qt::DirectConnection));
		QCoreApplication::processEvents();
		QCOMPARE(completed.size(), 1);
		QVERIFY(!QFileInfo::exists(path));
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
		QCOMPARE(manager.result().status, RenderStatus::Succeeded);
		QCOMPARE(manager.result().outputs.size(), 2);
		for (const auto& output : manager.result().outputs) { QVERIFY(output.encoderFinalized); }
	}

	void failedStartup_data()
	{
		QTest::addColumn<int>("format");
		QTest::newRow("inaccessible-directory-destination") << static_cast<int>(ProjectRenderer::ExportFileFormat::Wave);
		QTest::newRow("sentinel") << static_cast<int>(ProjectRenderer::ExportFileFormat::Count);
		QTest::newRow("negative-format") << -1;
		QTest::newRow("out-of-range-format") << 99;
	}

	void failedStartup()
	{
		QFETCH(int, format);
		QTemporaryDir directory;
		QVERIFY(directory.isValid());
		auto* originalDevice = Engine::audioEngine()->audioDev();
		RenderManager manager(settings(), static_cast<ProjectRenderer::ExportFileFormat>(format), directory.path());
		QSignalSpy completed(&manager, &RenderManager::completed);
		QSignalSpy finished(&manager, &RenderManager::finished);
		manager.renderProject();
		QCOMPARE(completed.size(), 1);
		QCOMPARE(finished.size(), 1);
		QCOMPARE(manager.result().status, RenderStatus::Failed);
		QCOMPARE(manager.result().outputs.size(), 1);
		QCOMPARE(manager.result().outputs.front().status, RenderStatus::Failed);
		QVERIFY(!manager.result().outputs.front().error.isEmpty());
		QVERIFY(Engine::audioEngine()->audioDev() == originalDevice);
		QVERIFY(QFileInfo(directory.path()).isDir());
		manager.renderProject();
		manager.abortProcessing();
		QCOMPARE(completed.size(), 1);
	}

	void partialBatchFailureRetainsSuccessAndRestoresMutes()
	{
		QTemporaryDir directory;
		QVERIFY(directory.isValid());
		auto* first = new SampleTrack(Engine::getSong());
		auto* second = new SampleTrack(Engine::getSong());
		first->setName("same");
		second->setName("same");
		QVERIFY(QDir(directory.path()).mkdir("1_same.wav"));
		auto* originalDevice = Engine::audioEngine()->audioDev();
		RenderManager manager(settings(), ProjectRenderer::ExportFileFormat::Wave, directory.path());
		QSignalSpy completed(&manager, &RenderManager::completed);
		manager.renderTracks();
		QTRY_COMPARE_WITH_TIMEOUT(completed.size(), 1, 30000);
		QCOMPARE(manager.result().status, RenderStatus::Failed);
		QCOMPARE(manager.result().outputs.size(), 2);
		QCOMPARE(manager.result().outputs[0].status, RenderStatus::Failed);
		QCOMPARE(manager.result().outputs[1].status, RenderStatus::Succeeded);
		QVERIFY(QFileInfo(directory.filePath("1_same.wav")).isDir());
		QVERIFY(readableFinalizedWave(directory.filePath("2_same.wav")));
		QVERIFY(!first->isMuted());
		QVERIFY(!second->isMuted());
		QVERIFY(Engine::audioEngine()->audioDev() == originalDevice);
	}

	void invalidBatchFormatFailsWithoutCreatingOutputs()
	{
		QTemporaryDir directory;
		auto* first = new SampleTrack(Engine::getSong());
		auto* second = new SampleTrack(Engine::getSong());
		RenderManager manager(settings(), static_cast<ProjectRenderer::ExportFileFormat>(-1), directory.path());
		QSignalSpy completed(&manager, &RenderManager::completed);
		manager.renderTracks();
		QCOMPARE(completed.size(), 1);
		QCOMPARE(manager.result().status, RenderStatus::Failed);
		QCOMPARE(manager.result().outputs.size(), 2);
		QCOMPARE(QDir(directory.path()).entryList(QDir::Files).size(), 0);
		QVERIFY(!first->isMuted());
		QVERIFY(!second->isMuted());
	}

	void emptyBatchIsFailedRatherThanSuccessful()
	{
		QTemporaryDir directory;
		auto* track = new SampleTrack(Engine::getSong());
		track->setMuted(true);
		RenderManager manager(settings(), ProjectRenderer::ExportFileFormat::Wave, directory.path());
		QSignalSpy completed(&manager, &RenderManager::completed);
		manager.renderTracks();
		QCOMPARE(completed.size(), 1);
		QCOMPARE(manager.result().status, RenderStatus::Failed);
		QVERIFY(manager.result().outputs.isEmpty());
		QVERIFY(!manager.result().error.isEmpty());
		QVERIFY(track->isMuted());
	}

	void multitrackCancellationRestoresOriginalMutes()
	{
		QTemporaryDir directory;
		auto* first = new SampleTrack(Engine::getSong());
		auto* second = new SampleTrack(Engine::getSong());
		auto* muted = new SampleTrack(Engine::getSong());
		muted->setMuted(true);
		auto* originalDevice = Engine::audioEngine()->audioDev();
		RenderManager manager(settings(), ProjectRenderer::ExportFileFormat::Wave, directory.path());
		QSignalSpy completed(&manager, &RenderManager::completed);
		manager.renderTracks();
		manager.abortProcessing();
		QCOMPARE(completed.size(), 1);
		QCOMPARE(manager.result().status, RenderStatus::Cancelled);
		QVERIFY(!first->isMuted());
		QVERIFY(!second->isMuted());
		QVERIFY(muted->isMuted());
		QCOMPARE(QDir(directory.path()).entryList(QDir::Files).size(), 0);
		QVERIFY(Engine::audioEngine()->audioDev() == originalDevice);
	}

	void destructionDuringRenderJoinsAndCleansUp()
	{
		QTemporaryDir directory;
		new SampleTrack(Engine::getSong());
		const auto path = directory.filePath("destroy.wav");
		auto* originalDevice = Engine::audioEngine()->audioDev();
		{
			RenderManager manager(settings(), ProjectRenderer::ExportFileFormat::Wave, path);
			manager.renderProject();
		}
		QVERIFY(!QFileInfo::exists(path));
		QVERIFY(Engine::audioEngine()->audioDev() == originalDevice);
	}

	void completionListenerMayDeleteTheManager()
	{
		QTemporaryDir directory;
		new SampleTrack(Engine::getSong());
		auto* originalDevice = Engine::audioEngine()->audioDev();
		auto* manager = new RenderManager(settings(), ProjectRenderer::ExportFileFormat::Wave, directory.filePath("listener.wav"));
		QPointer<RenderManager> guard(manager);
		connect(manager, &RenderManager::completed, this, [manager](const RenderResult&) { delete manager; });
		manager->renderProject();
		QTRY_VERIFY_WITH_TIMEOUT(guard.isNull(), 30000);
		QVERIFY(Engine::audioEngine()->audioDev() == originalDevice);
		QVERIFY(readableFinalizedWave(directory.filePath("listener.wav")));
	}

	void availableEncodersFinalize_data()
	{
		QTest::addColumn<int>("format");
		for (const auto& encoder : ProjectRenderer::fileEncodeDevices)
		{
			if (encoder.isAvailable()) { QTest::newRow(encoder.m_extension) << static_cast<int>(encoder.m_fileFormat); }
		}
	}

	void availableEncodersFinalize()
	{
		QFETCH(int, format);
		QTemporaryDir directory;
		new SampleTrack(Engine::getSong());
		const auto exportFormat = static_cast<ProjectRenderer::ExportFileFormat>(format);
		const auto path = directory.filePath(QString::fromUtf8("encoder 音符 é") + ProjectRenderer::getFileExtensionFromFormat(exportFormat));
		RenderManager manager(settings(), exportFormat, path);
		QSignalSpy completed(&manager, &RenderManager::completed);
		manager.renderProject();
		QTRY_COMPARE_WITH_TIMEOUT(completed.size(), 1, 30000);
		QCOMPARE(manager.result().status, RenderStatus::Succeeded);
		QVERIFY(manager.result().outputs.front().encoderFinalized);
		int type = SF_FORMAT_WAV;
		switch (exportFormat)
		{
		case ProjectRenderer::ExportFileFormat::Flac: type = SF_FORMAT_FLAC; break;
		case ProjectRenderer::ExportFileFormat::Ogg: type = SF_FORMAT_OGG; break;
		case ProjectRenderer::ExportFileFormat::MP3: type = SF_FORMAT_MPEG; break;
		default: break;
		}
		QVERIFY(readableFinalizedAudio(path, type));
	}
};

QTEST_GUILESS_MAIN(RenderManagerLifecycleTest)
#include "RenderManagerLifecycleTest.moc"
