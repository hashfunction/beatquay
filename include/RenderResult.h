// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef LMMS_RENDER_RESULT_H
#define LMMS_RENDER_RESULT_H
#include <QList>
#include <QMetaType>
#include <QString>

namespace lmms
{
enum class RenderStatus { Succeeded, Failed, Cancelled };

struct RenderOutputResult
{
	QString path;
	RenderStatus status = RenderStatus::Failed;
	bool encoderFinalized = false;
	bool partialOutputRemoved = false;
	QString error;
};

struct RenderResult
{
	RenderStatus status = RenderStatus::Failed;
	QList<RenderOutputResult> outputs;
	QString error;
};
} // namespace lmms
Q_DECLARE_METATYPE(lmms::RenderResult)
#endif // LMMS_RENDER_RESULT_H
