// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include <QtTest>
#include <QCryptographicHash>
#include <QTemporaryDir>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include "ConfigManager.h"
#include "DataFile.h"
#include "Engine.h"
#include "InstrumentTrack.h"
#include "Instrument.h"
#include "MidiClip.h"
#include "ProjectExportFactsCollector.h"
#include "RenderManager.h"
#include "Song.h"
#include <sndfile.h>
#include <cmath>
#ifdef Q_OS_WIN
#include <windows.h>
#include <tlhelp32.h>
#endif
using namespace lmms;

class BeatQuayTemplateTest : public QObject
{
	Q_OBJECT
	QTemporaryDir m_work;
	QMap<QString, QByteArray> m_pluginHashes;
	bool m_engineStarted = false;
	static QByteArray hash(const QString& path)
	{
		QFile file(path);
		if (!file.open(QIODevice::ReadOnly)) { return {}; }
		QCryptographicHash sha(QCryptographicHash::Sha256);
		return sha.addData(&file) ? sha.result().toHex() : QByteArray{};
	}
	static QJsonObject semantics()
	{
		QJsonArray tracks;
		for (auto* base : Engine::getSong()->tracks())
		{
			auto* track = dynamic_cast<InstrumentTrack*>(base);
			if (!track || !track->instrument()) { return {}; }
			QJsonArray clips;
			for (auto* baseClip : track->getClips())
			{
				auto* clip = dynamic_cast<MidiClip*>(baseClip);
				if (!clip) { return {}; }
				QJsonArray notes;
				for (const auto* note : clip->notes())
				{
					notes.append(QJsonArray{note->pos().getTicks(), note->key(), note->length().getTicks(), note->getVolume(), note->getPanning()});
				}
				clips.append(QJsonObject{{"name", clip->name()}, {"pos", clip->startPosition().getTicks()},
					{"len", clip->length().getTicks()}, {"muted", clip->isMuted()}, {"notes", notes}});
			}
			QDomDocument doc;
			auto parent = doc.createElement("settings"); doc.appendChild(parent);
			const auto saved = track->instrument()->saveState(doc, parent);
			QJsonObject settings;
			for (int i = 0; i < saved.attributes().size(); ++i)
			{
				const auto attribute = saved.attributes().item(i).toAttr();
				settings.insert(attribute.name(), attribute.value());
			}
			tracks.append(QJsonObject{{"name", track->name()}, {"instrument", track->instrument()->nodeName()},
				{"volume", track->getVolume()}, {"base", track->baseNoteModel()->value()},
				{"muted", track->isMuted()}, {"settings", settings}, {"clips", clips}});
		}
		return {{"tempo", Engine::getSong()->getTempo()}, {"bars", Engine::getSong()->length()}, {"tracks", tracks}};
	}
	void checkNativeModules()
	{
#ifdef Q_OS_WIN
		QVERIFY(GetModuleHandleW(L"lmms.exe") == GetModuleHandleW(nullptr));
		const auto snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, GetCurrentProcessId());
		QVERIFY(snapshot != INVALID_HANDLE_VALUE);
		MODULEENTRY32W module{}; module.dwSize = static_cast<DWORD>(sizeof(module));
		QMap<QString, QString> observed;
		int hostCount = 0;
		if (Module32FirstW(snapshot, &module))
		{
			do
			{
				const auto path = QString::fromWCharArray(module.szExePath);
				const auto name = QFileInfo(path).fileName().toLower();
				if (name == "lmms.exe") { ++hostCount; }
				if (name == "lmms.exe" || name == "kicker.dll" || name == "tripleoscillator.dll") { observed.insert(name, path); }
			} while (Module32NextW(snapshot, &module));
		}
		CloseHandle(snapshot);
		QCOMPARE(hostCount, 1);
		QCOMPARE(QFileInfo(observed.value("lmms.exe")).canonicalFilePath().toCaseFolded(), QFileInfo(QCoreApplication::applicationFilePath()).canonicalFilePath().toCaseFolded());
		QJsonArray evidence;
		for (auto it = m_pluginHashes.cbegin(); it != m_pluginHashes.cend(); ++it)
		{
			const auto actual = observed.value(QFileInfo(it.key()).fileName().toLower());
			QVERIFY(!actual.isEmpty());
			QCOMPARE(QFileInfo(actual).canonicalFilePath().toCaseFolded(), QFileInfo(it.key()).canonicalFilePath().toCaseFolded());
			QCOMPARE(hash(actual), it.value());
			evidence.append(QJsonObject{{"path", actual}, {"sha256", QString::fromLatin1(it.value())}, {"matches_preload_bytes", true}});
		}
		qInfo().noquote() << QJsonDocument(QJsonObject{{"qualification_test_host", QCoreApplication::applicationFilePath()},
			{"secondary_lmms_module_count", hostCount - 1}, {"actual_synth_modules", evidence}}).toJson(QJsonDocument::Compact);
#endif
	}
private slots:
	void initTestCase()
	{
		QVERIFY(m_work.isValid());
		QDir::setSearchPaths("plugins", {QStringLiteral(BEATQUAY_KICKER_DIR), QStringLiteral(BEATQUAY_TRIPLE_DIR)});
		qunsetenv("LMMS_PLUGIN_DIR");
		QFile config(m_work.filePath("config.xml"));
		QVERIFY(config.open(QIODevice::WriteOnly | QIODevice::NewOnly));
		QVERIFY(config.write("<lmms/>") > 0); config.close();
		ConfigManager::inst()->loadConfigFile(config.fileName());
		ConfigManager::inst()->setWorkingDir(m_work.filePath("user/"));
		for (const auto& path : {QStringLiteral(BEATQUAY_KICKER_FILE), QStringLiteral(BEATQUAY_TRIPLE_FILE)})
		{
			const auto sha = hash(path); QVERIFY(!sha.isEmpty()); m_pluginHashes.insert(path, sha);
		}
		Engine::init(true);
		m_engineStarted = true;
		DataFile current(DataFile::Type::SongProjectTemplate);
		QCOMPARE(current.documentElement().attribute("version"), QString("31"));
	}
	void cleanupTestCase() { if (m_engineStarted) { Engine::destroy(); } }
	void loadRoundTripAndRender_data()
	{
		QTest::addColumn<QString>("name"); QTest::addColumn<int>("bars"); QTest::addColumn<int>("tempo");
		QTest::addColumn<int>("tracks"); QTest::addColumn<int>("notes"); QTest::addColumn<QString>("synth");
		QTest::newRow("four-bar-drum-grid") << QString("BeatQuay-Drum-Grid.mpt") << 4 << 112 << 3 << 55 << QString("kicker");
		QTest::newRow("eight-bar-bassline") << QString("BeatQuay-Bassline-Sketch.mpt") << 8 << 108 << 1 << 40 << QString("tripleoscillator");
	}
	void loadRoundTripAndRender()
	{
		QFETCH(QString, name); QFETCH(int, bars); QFETCH(int, tempo); QFETCH(int, tracks); QFETCH(int, notes); QFETCH(QString, synth);
		const auto path = QDir(QStringLiteral(BEATQUAY_TEMPLATE_DIR)).filePath(name);
		const auto originalHash = hash(path); QVERIFY(!originalHash.isEmpty());
		auto* song = Engine::getSong();
		song->createNewProjectFromTemplate(path);
		QVERIFY2(!song->hasErrors(), qPrintable(song->errorSummary()));
		QVERIFY(song->projectFileName().isEmpty());
		QCOMPARE(song->tracks().size(), static_cast<std::size_t>(tracks));
		QCOMPARE(song->getTempo(), tempo); QCOMPARE(song->length(), bars);
		const auto original = semantics(); QVERIFY(!original.isEmpty());
		int observedNotes = 0;
		for (const auto& value : original.value("tracks").toArray())
		{
			const auto track = value.toObject(); QCOMPARE(track.value("instrument").toString(), synth);
			QCOMPARE(track.value("clips").toArray().size(), bars);
			for (const auto& clip : track.value("clips").toArray()) { observedNotes += clip.toObject().value("notes").toArray().size(); }
		}
		QCOMPARE(observedNotes, notes);
		// Compare the loaded model to the authored XML, not merely to itself
		// after a save: a loader that shifted every key must fail this check.
		DataFile authored(path);
		auto sourceTrack = authored.content().firstChildElement("trackcontainer").firstChildElement("track");
		for (const auto& value : original.value("tracks").toArray())
		{
			QVERIFY(!sourceTrack.isNull());
			const auto actual = value.toObject();
			const auto sourceSettings = sourceTrack.firstChildElement("instrumenttrack").firstChildElement("instrument").firstChildElement();
			for (int i = 0; i < sourceSettings.attributes().size(); ++i)
			{
				const auto attribute = sourceSettings.attributes().item(i).toAttr();
				const auto saved = actual.value("settings").toObject();
				QVERIFY(saved.contains(attribute.name()));
				QVERIFY(std::abs(saved.value(attribute.name()).toString().toDouble() - attribute.value().toDouble()) < 0.0001);
			}
			auto sourceClip = sourceTrack.firstChildElement("midiclip");
			for (const auto& actualClipValue : actual.value("clips").toArray())
			{
				QVERIFY(!sourceClip.isNull()); const auto actualClip = actualClipValue.toObject();
				QCOMPARE(actualClip.value("pos").toInt(), sourceClip.attribute("pos").toInt());
				QCOMPARE(actualClip.value("len").toInt(), sourceClip.attribute("len").toInt());
				auto sourceNote = sourceClip.firstChildElement("note");
				for (const auto& actualNote : actualClip.value("notes").toArray())
				{
					QVERIFY(!sourceNote.isNull());
					const QJsonArray expected{sourceNote.attribute("pos").toInt(), sourceNote.attribute("key").toInt(),
						sourceNote.attribute("len").toInt(), sourceNote.attribute("vol").toInt(), sourceNote.attribute("pan").toInt()};
					QCOMPARE(actualNote.toArray(), expected); sourceNote = sourceNote.nextSiblingElement("note");
				}
				QVERIFY(sourceNote.isNull()); sourceClip = sourceClip.nextSiblingElement("midiclip");
			}
			QVERIFY(sourceClip.isNull()); sourceTrack = sourceTrack.nextSiblingElement("track");
		}
		QVERIFY(sourceTrack.isNull());
		checkNativeModules();
		const auto roundTrip = m_work.filePath(name + QString::fromUtf8(" 音符 roundtrip.mmp"));
		QVERIFY(song->saveProjectFile(roundTrip));
		song->loadProject(roundTrip);
		QVERIFY2(!song->hasErrors(), qPrintable(song->errorSummary()));
		QCOMPARE(semantics(), original);
		const auto output = m_work.filePath(name + QString::fromUtf8(" 音符.wav"));
		const auto facts = ProjectExportFactsCollector::collect(ProjectRenderer::ExportFileFormat::Wave, {output}, false, false, 1);
		QCOMPARE(facts.outputs.size(), 1); QVERIFY(facts.outputs[0].resources.isEmpty());
		QVERIFY(ProjectExportCheck::beforeExport(facts.outputs[0]).isEmpty());
		song->setExportLoop(false); song->setRenderBetweenMarkers(false); song->setLoopRenderCount(1);
		RenderManager manager({44100, 160, OutputSettings::BitDepth::Depth16Bit, OutputSettings::StereoMode::Stereo}, ProjectRenderer::ExportFileFormat::Wave, output);
		QSignalSpy completed(&manager, &RenderManager::completed);
		manager.renderProject(); QTRY_COMPARE_WITH_TIMEOUT(completed.size(), 1, 30000);
		QCOMPARE(manager.result().status, RenderStatus::Succeeded);
		QFile audio(output); QVERIFY(audio.open(QIODevice::ReadOnly));
		SF_INFO info{}; auto* stream = sf_open_fd(audio.handle(), SFM_READ, &info, SF_FALSE); QVERIFY(stream);
		short samples[2048]{}; int peak = 0; double squares = 0; sf_count_t count = 0;
		for (sf_count_t read; (read = sf_read_short(stream, samples, 2048)) > 0; )
		{ for (sf_count_t i = 0; i < read; ++i) { peak = std::max(peak, std::abs(static_cast<int>(samples[i]))); squares += static_cast<double>(samples[i]) * samples[i]; } count += read; }
		QCOMPARE(sf_close(stream), 0); QCOMPARE(info.channels, 2); QCOMPARE(info.samplerate, 44100);
		QCOMPARE(info.format & SF_FORMAT_SUBMASK, SF_FORMAT_PCM_16); QCOMPARE(count, info.frames * 2);
		QVERIFY(std::abs(static_cast<double>(info.frames) / info.samplerate - (bars + 1) * 240.0 / tempo) < 0.25);
		QVERIFY(peak >= 100); QVERIFY(peak < 32767); QVERIFY(count > 0 && std::sqrt(squares / count) > 10);
		QCOMPARE(hash(path), originalHash); QCOMPARE(semantics(), original);
		qInfo().noquote() << QJsonDocument(QJsonObject{{"template", path}, {"template_sha256", QString::fromLatin1(originalHash)},
			{"roundtrip_verified", true}, {"rendered_frames", static_cast<double>(info.frames)}, {"peak_pcm16", peak},
			{"output_sha256", QString::fromLatin1(hash(output))}, {"original_unchanged", true}}).toJson(QJsonDocument::Compact);
	}
};
QTEST_GUILESS_MAIN(BeatQuayTemplateTest)
#include "BeatQuayTemplateTest.moc"
