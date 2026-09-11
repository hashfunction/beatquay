// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include "Track.h"
#include <QRegularExpression>
#include <QtTest>

using namespace lmms;

class TrackFilenameFilterTest : public QObject
{
	Q_OBJECT
private slots:
	void patternIsValid()
	{
		const QRegularExpression filter(FILENAME_FILTER);
		QVERIFY2(filter.isValid(), qPrintable(filter.errorString()));
	}

	void filtersOnlyTheIntendedAsciiCharacters_data()
	{
		QTest::addColumn<int>("code");
		for (int code = 0; code < 128; ++code)
		{
			QTest::newRow(qPrintable(QString::number(code))) << code;
		}
	}

	void filtersOnlyTheIntendedAsciiCharacters()
	{
		QFETCH(int, code);
		const QChar character(code);
		const bool forbidden = code < 32 || code == 127 || QStringLiteral("\"*/:<>?\\|").contains(character);
		const QString original = QStringLiteral("before") + character + QStringLiteral("after");
		const QString expected = forbidden ? QStringLiteral("beforeafter") : original;
		QCOMPARE(QString(original).remove(QRegularExpression(FILENAME_FILTER)), expected);
	}

	void preservesUnicodeAndRemovesMixedForbiddenCharacters()
	{
		const QString unicode = QString::fromUtf8("音符 é e\xCC\x81 🎵");
		const QRegularExpression filter(FILENAME_FILTER);
		QCOMPARE(QString(unicode).remove(filter), unicode);
		const QString mixed = QStringLiteral("\"*/:<>?\\|") + QChar(0) + QChar(31) + unicode + QChar(127);
		QCOMPARE(QString(mixed).remove(filter), unicode);
		QCOMPARE(QString().remove(filter), QString());
	}
};

QTEST_GUILESS_MAIN(TrackFilenameFilterTest)
#include "TrackFilenameFilterTest.moc"
