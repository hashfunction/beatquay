// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "AudioFileOutput.h"

namespace lmms
{
bool AudioFileOutput::open(bool requireNew)
{
	if (m_opened || m_finalized) { return false; }
	m_opened = m_file.open(QIODevice::WriteOnly | (requireNew ? QIODevice::NewOnly : QIODevice::Truncate));
	if (m_opened) { m_identity = exportFileIdentity(m_file.handle()); }
	return m_opened;
}

qint64 AudioFileOutput::write(const char* data, qint64 size)
{
	const auto written = m_file.isOpen() && !m_finalized ? m_file.write(data, size) : -1;
	if (written < 0 || written != size) { recordWriteFailure(); }
	return written;
}

bool AudioFileOutput::finalize(const std::function<bool()>& finishEncoder)
{
	if (m_finalized) { return m_success; }
	// Encoders may still write trailers here. Do not mark finalized or close the
	// descriptor until that work is complete, even when an earlier write failed.
	const bool encoderSucceeded = finishEncoder();
	const bool flushed = m_file.isOpen() && m_file.flush();
	m_file.close();
	m_success = encoderSucceeded && flushed && !m_writeFailed;
	m_finalized = true;
	return m_success;
}

bool AudioFileOutput::removePartial()
{
	if (!m_opened || !m_finalized || !m_identity) { return false; }
	return removeOwnedExportFile(m_file.fileName(), *m_identity, &m_cleanupRecoveryPath);
}
} // namespace lmms
