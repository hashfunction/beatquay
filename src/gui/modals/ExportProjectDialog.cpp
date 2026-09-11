/*
 * ExportProjectDialog.cpp - implementation of dialog for exporting project
 *
 * Copyright (c) 2004-2013 Tobias Doerffel <tobydox/at/users.sourceforge.net>
 *
 * This file is part of LMMS - https://lmms.io
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program (see COPYING); if not, write to the
 * Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
 * Boston, MA 02110-1301 USA.
 *
 */

#include "ExportProjectDialog.h"
#include "ProjectExportFactsCollector.h"
#include "ProjectExportCheckDialog.h"

#include <algorithm>
#include <QCheckBox>
#include <QComboBox>
#include <QDir>
#include <QFileInfo>
#include <QFormLayout>
#include <QGroupBox>
#include <QLabel>
#include <QProgressBar>
#include <QPushButton>
#include <QSpinBox>
#include <QVBoxLayout>

#include "Engine.h"
#include "AudioEngine.h"
#include "ProjectRenderer.h"
#include "Song.h"

namespace lmms::gui {

namespace {
constexpr auto maxCompressionLevel = 8;
constexpr auto defaultCompressionLevel = 5;
constexpr auto defaultBitRate = SUPPORTED_BITRATES[2];
constexpr auto defaultBitDepth = OutputSettings::BitDepth::Depth24Bit;
constexpr auto defaultStereoMode = OutputSettings::StereoMode::Stereo;
constexpr auto maxLoopRepeat = std::numeric_limits<int>::max();
} // namespace

ExportProjectDialog::ExportProjectDialog(const QString& path, Mode mode, QWidget* parent)
	: QDialog(parent)
	, m_fileFormatLabel(new QLabel(tr("File format:")))
	, m_fileFormatComboBox(new QComboBox())
	, m_sampleRateLabel(new QLabel(tr("Sampling rate:")))
	, m_sampleRateComboBox(new QComboBox())
	, m_bitRateLabel(new QLabel(tr("Bit rate:")))
	, m_bitRateComboBox(new QComboBox())
	, m_bitDepthLabel(new QLabel(tr("Bit depth:")))
	, m_bitDepthComboBox(new QComboBox())
	, m_stereoModeLabel(new QLabel(("Stereo mode:")))
	, m_stereoModeComboBox(new QComboBox())
	, m_compressionLevelLabel(new QLabel(tr("Compression level:")))
	, m_compressionLevelComboBox(new QComboBox())
	, m_fileFormatSettingsGroupBox(new QGroupBox(tr("File format settings")))
	, m_fileFormatSettingsLayout(new QFormLayout(m_fileFormatSettingsGroupBox))
	, m_exportAsLoopBox(new QCheckBox(tr("Export as loop (remove extra bar)")))
	, m_exportBetweenLoopMarkersBox(new QCheckBox(tr("Export between loop markers")))
	, m_loopRepeatLabel(new QLabel(tr("Render looped section:")))
	, m_loopRepeatBox(new QSpinBox())
	, m_startButton(new QPushButton(tr("Start")))
	, m_cancelButton(new QPushButton(tr("Cancel")))
	, m_progressBar(new QProgressBar())
	, m_path(path)
	, m_mode(mode)
{
	setWindowTitle(tr("Export project"));

	for (const auto& device : ProjectRenderer::fileEncodeDevices)
	{
		if (!device.isAvailable()) { continue; }
		m_fileFormatComboBox->addItem(tr(device.m_description), static_cast<int>(device.m_fileFormat));
	}

	for (const auto& sampleRate : SUPPORTED_SAMPLERATES)
	{
		const auto str = tr("%1 %2").arg(QString::number(sampleRate), "Hz");
		m_sampleRateComboBox->addItem(str, sampleRate);
	}

	for (const auto& bitRate : SUPPORTED_BITRATES)
	{
		const auto str = tr("%1 %2").arg(QString::number(bitRate), "KBit/s");
		m_bitRateComboBox->addItem(str, bitRate);
	}

	for (auto i = 0; i < static_cast<int>(OutputSettings::BitDepth::Count); ++i)
	{
		switch (static_cast<OutputSettings::BitDepth>(i))
		{
		case OutputSettings::BitDepth::Depth16Bit:
			m_bitDepthComboBox->addItem(tr("16 Bit integer"), i);
			break;
		case OutputSettings::BitDepth::Depth24Bit:
			m_bitDepthComboBox->addItem(tr("24 Bit integer"), i);
			break;
		case OutputSettings::BitDepth::Depth32Bit:
			m_bitDepthComboBox->addItem(tr("32 Bit float"), i);
			break;
		default:
			assert(false && "invalid or unsupported bit depth");
			break;
		}
	}

	for (auto i = 0; i < static_cast<int>(OutputSettings::StereoMode::Count); ++i)
	{
		switch (static_cast<OutputSettings::StereoMode>(i))
		{
		case OutputSettings::StereoMode::Mono:
			m_stereoModeComboBox->addItem(tr("Mono"), i);
			break;
		case OutputSettings::StereoMode::Stereo:
			m_stereoModeComboBox->addItem(tr("Stereo"), i);
			break;
		case OutputSettings::StereoMode::JointStereo:
			m_stereoModeComboBox->addItem(tr("Joint stereo"), i);
			break;
		default:
			assert(false && "invalid or unsupported stereo mode");
			break;
		}
	}

	for (auto i = 0; i <= maxCompressionLevel; ++i)
	{
		const auto compressionValue = static_cast<float>(i) / maxCompressionLevel;
		switch (i)
		{
		case 0:
			m_compressionLevelComboBox->addItem(tr("%1 (Fastest, biggest)").arg(i), compressionValue);
			break;
		case maxCompressionLevel:
			m_compressionLevelComboBox->addItem(tr("%1 (Slowest, smallest)").arg(i), compressionValue);
			break;
		default:
			m_compressionLevelComboBox->addItem(QString::number(i), compressionValue);
			break;
		}
	}


	auto loopRepeatLayout = new QHBoxLayout{};
	loopRepeatLayout->addWidget(m_loopRepeatLabel);
	loopRepeatLayout->addWidget(m_loopRepeatBox);

	auto exportSettingsGroupBox = new QGroupBox(tr("Export settings"));
	auto exportSettingsLayout = new QVBoxLayout{exportSettingsGroupBox};
	exportSettingsLayout->addWidget(m_exportAsLoopBox);
	exportSettingsLayout->addWidget(m_exportBetweenLoopMarkersBox);
	exportSettingsLayout->addLayout(loopRepeatLayout);

	m_fileFormatSettingsLayout->addRow(m_fileFormatLabel, m_fileFormatComboBox);

	auto startCancelButtonsLayout = new QHBoxLayout{};
	startCancelButtonsLayout->addStretch();
	startCancelButtonsLayout->addWidget(m_startButton);
	startCancelButtonsLayout->addWidget(m_cancelButton);

	auto mainLayout = new QVBoxLayout(this);
	mainLayout->addWidget(exportSettingsGroupBox);
	mainLayout->addWidget(m_fileFormatSettingsGroupBox);
	mainLayout->addStretch();
	mainLayout->addLayout(startCancelButtonsLayout);
	mainLayout->addWidget(m_progressBar);

	m_progressBar->setValue(0);
	m_loopRepeatBox->setRange(1, maxLoopRepeat);
	m_loopRepeatBox->setValue(1);
	m_loopRepeatBox->setSuffix(tr(" time(s)"));

	m_fileFormatComboBox->setCurrentIndex(-1);
	connect(m_fileFormatComboBox, qOverload<int>(&QComboBox::currentIndexChanged), this,
		&ExportProjectDialog::onFileFormatChanged);

	const auto pathExtension = QFileInfo{path}.suffix().prepend(".");
	const auto pathFormat = ProjectRenderer::getFileFormatFromExtension(pathExtension);

	m_fileFormatComboBox->setCurrentIndex(std::max(0, m_fileFormatComboBox->findData(static_cast<int>(pathFormat))));
	m_bitRateComboBox->setCurrentIndex(std::max(0, m_bitRateComboBox->findData(defaultBitRate)));
	m_bitDepthComboBox->setCurrentIndex(std::max(0, m_bitDepthComboBox->findData(static_cast<int>(defaultBitDepth))));
	m_stereoModeComboBox->setCurrentIndex(
		std::max(0, m_stereoModeComboBox->findData(static_cast<int>(defaultStereoMode))));
	m_compressionLevelComboBox->setCurrentIndex(defaultCompressionLevel);

	connect(m_startButton, &QPushButton::clicked, this, &ExportProjectDialog::onStartButtonClicked);
	connect(m_cancelButton, &QPushButton::clicked, this, &ExportProjectDialog::reject);
}

ExportProjectDialog::~ExportProjectDialog()
{
	m_renderManager.reset();
	restoreExportSettings();
}

void ExportProjectDialog::onFileFormatChanged(int index)
{
	index = m_fileFormatComboBox->itemData(index).toInt();
	if (m_mode == Mode::ExportProject)
	{
		const auto fileInfo = QFileInfo{m_path};
		const auto extension
			= ProjectRenderer::getFileExtensionFromFormat(static_cast<ProjectRenderer::ExportFileFormat>(index));
		m_path = fileInfo.path() + QDir::separator() + fileInfo.completeBaseName() + extension;
	}

	// Remove and detach all rows after the file format row
	while (m_fileFormatSettingsLayout->rowCount() > 1)
	{
		const auto& [label, field] = m_fileFormatSettingsLayout->takeRow(1);
		label->widget()->setParent(nullptr);
		field->widget()->setParent(nullptr);
	}

	switch (static_cast<ProjectRenderer::ExportFileFormat>(index))
	{
	case ProjectRenderer::ExportFileFormat::Wave:
		m_fileFormatSettingsLayout->addRow(m_sampleRateLabel, m_sampleRateComboBox);
		m_fileFormatSettingsLayout->addRow(m_bitDepthLabel, m_bitDepthComboBox);
		break;
	case ProjectRenderer::ExportFileFormat::Flac:
		m_fileFormatSettingsLayout->addRow(m_sampleRateLabel, m_sampleRateComboBox);
		m_fileFormatSettingsLayout->addRow(m_bitDepthLabel, m_bitDepthComboBox);
		m_fileFormatSettingsLayout->addRow(m_compressionLevelLabel, m_compressionLevelComboBox);
		break;
	case ProjectRenderer::ExportFileFormat::Ogg:
		m_fileFormatSettingsLayout->addRow(m_sampleRateLabel, m_sampleRateComboBox);
		m_fileFormatSettingsLayout->addRow(m_bitRateLabel, m_bitRateComboBox);
		break;
	case ProjectRenderer::ExportFileFormat::MP3:
		m_fileFormatSettingsLayout->addRow(m_stereoModeLabel, m_stereoModeComboBox);
		m_fileFormatSettingsLayout->addRow(m_bitRateLabel, m_bitRateComboBox);
	default:
		break;
	}
}

void ExportProjectDialog::onStartButtonClicked()
{
	const auto sampleRate = static_cast<sample_rate_t>(m_sampleRateComboBox->currentData().toInt());
	const auto bitRate = static_cast<bitrate_t>(m_bitRateComboBox->currentData().toInt());
	const auto bitDepth = static_cast<OutputSettings::BitDepth>(m_bitDepthComboBox->currentData().toInt());
	const auto stereoMode = static_cast<OutputSettings::StereoMode>(m_stereoModeComboBox->currentData().toInt());
	auto outputSettings = OutputSettings{sampleRate, bitRate, bitDepth, stereoMode};

	const auto compressionLevel = m_compressionLevelComboBox->currentData().toDouble();
	outputSettings.setCompressionLevel(compressionLevel);

	const auto format = static_cast<ProjectRenderer::ExportFileFormat>(m_fileFormatComboBox->currentData().toInt());
	if (m_renderManager) { return; }
	setRendering(true);
	const auto paths = RenderManager::outputPaths(format, m_path, m_mode == Mode::ExportTracks);
	const auto collected = ProjectExportFactsCollector::collect(format, paths,
		m_exportBetweenLoopMarkersBox->isChecked(), m_exportAsLoopBox->isChecked(), m_loopRepeatBox->value());
	m_exportSession = std::make_unique<ProjectExportSession>(collected.outputs, collected.protectedPaths);
	if (!ProjectExportCheckDialog::confirm(m_exportSession->issues(), this))
	{
		m_exportSession->start(ProjectExportSession::Decision::Cancel, [](const auto&, const auto&) {});
		setRendering(false);
		return;
	}
	const bool started = m_exportSession->start(ProjectExportSession::Decision::Continue, [&](const auto& destinations, const auto& protectedPaths)
	{
		auto* song = Engine::getSong();
		m_previousExportLoop = song->exportLoop();
		m_previousBetweenMarkers = song->renderBetweenMarkers();
		m_previousLoopCount = song->getLoopRenderCount();
		m_exportSettingsSaved = true;
		song->setExportLoop(m_exportAsLoopBox->isChecked());
		song->setRenderBetweenMarkers(m_exportBetweenLoopMarkersBox->isChecked());
		song->setLoopRenderCount(m_loopRepeatBox->value());
		m_renderManager = std::make_unique<RenderManager>(outputSettings, format, m_path, destinations, protectedPaths);
		connect(m_renderManager.get(), &RenderManager::progressChanged, m_progressBar, &QProgressBar::setValue);
		connect(m_renderManager.get(), &RenderManager::progressChanged, this, &ExportProjectDialog::updateTitleBar);
		connect(m_renderManager.get(), &RenderManager::completed, this, &ExportProjectDialog::onRenderCompleted);
		if (m_mode == Mode::ExportTracks) { m_renderManager->renderTracks(); }
		else { m_renderManager->renderProject(); }
	});
	if (!started)
	{
		ProjectExportCheckDialog::confirm(m_exportSession->issues(), this);
		setRendering(false);
	}
}

void ExportProjectDialog::accept()
{
	if (m_renderManager && !m_renderManager->isComplete()) { return; }
	restoreExportSettings();
	m_renderManager.reset();
	QDialog::accept();
}

void ExportProjectDialog::reject()
{
	if (m_renderManager && !m_renderManager->isComplete())
	{
		m_renderManager->abortProcessing(); // Typed completion handles cleanup/error disclosure.
		return;
	}
	restoreExportSettings();
	m_renderManager.reset();
	QDialog::reject();
}

void ExportProjectDialog::restoreExportSettings()
{
	if (!m_exportSettingsSaved) { return; }
	auto* song = Engine::getSong();
	song->setExportLoop(m_previousExportLoop);
	song->setRenderBetweenMarkers(m_previousBetweenMarkers);
	song->setLoopRenderCount(m_previousLoopCount);
	m_exportSettingsSaved = false;
}

void ExportProjectDialog::setRendering(bool rendering)
{
	m_startButton->setEnabled(!rendering);
	m_fileFormatSettingsGroupBox->setEnabled(!rendering);
	m_exportAsLoopBox->setEnabled(!rendering);
	m_exportBetweenLoopMarkersBox->setEnabled(!rendering);
	m_loopRepeatBox->setEnabled(!rendering);
	if (!rendering) { setWindowTitle(tr("Export project")); }
}

void ExportProjectDialog::onRenderCompleted(RenderResult result)
{
	const auto issues = m_exportSession->postflight(result);
	restoreExportSettings();
	m_renderManager.reset();
	setRendering(false);
	const bool cancellationResidue = std::any_of(result.outputs.begin(), result.outputs.end(), [](const auto& output)
	{ return output.status == RenderStatus::Succeeded || !output.error.isEmpty() || !output.retainedPartialPath.isEmpty() || !output.cleanupRecoveryPath.isEmpty(); });
	if (result.status != RenderStatus::Cancelled || cancellationResidue)
	{ ProjectExportCheckDialog::showResult(result, issues, this); }
	if (result.status == RenderStatus::Succeeded) { QDialog::accept(); }
	else if (result.status == RenderStatus::Cancelled) { QDialog::reject(); }
}

void ExportProjectDialog::updateTitleBar(int prog)
{
	setWindowTitle(tr("Rendering: %1%").arg(prog));
}

} // namespace lmms::gui
