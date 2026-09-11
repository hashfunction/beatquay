// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef LMMS_AUDIO_FILE_OUTPUT_H
#define LMMS_AUDIO_FILE_OUTPUT_H
#include <QFile>
#include <functional>
#include "lmms_export.h"

namespace lmms
{
// Owns the output file, while AudioFileDevice owns the encoder. Explicitly
// finalize the encoder before closing its descriptor or removing partial output.
class LMMS_EXPORT AudioFileOutput
{
public:
	explicit AudioFileOutput(const QString& path) : m_file(path) {}
	bool open();
	bool isOpen() const { return m_file.isOpen(); }
	QString fileName() const { return m_file.fileName(); }
	int handle() const { return m_file.handle(); }
	qint64 write(const char* data, qint64 size);
	void recordWriteFailure() { m_writeFailed = true; }
	bool hasWriteFailure() const { return m_writeFailed; }
	bool finalize(const std::function<bool()>& finishEncoder);
	bool removePartial();
private:
	QFile m_file;
	bool m_opened = false;
	bool m_writeFailed = false;
	bool m_finalized = false;
	bool m_success = false;
};
} // namespace lmms
#endif // LMMS_AUDIO_FILE_OUTPUT_H
