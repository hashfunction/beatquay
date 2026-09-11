// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#ifndef LMMS_GUI_PROJECT_EXPORT_CHECK_DIALOG_H
#define LMMS_GUI_PROJECT_EXPORT_CHECK_DIALOG_H
#include "ProjectExportCheck.h"
#include "RenderResult.h"
class QWidget;
namespace lmms::gui
{
class ProjectExportCheckDialog
{
public:
	static bool confirm(const QList<ProjectExportIssue>& issues, QWidget* parent);
	static void showResult(const RenderResult& result, const QList<ProjectExportIssue>& issues, QWidget* parent);
};
}
#endif
