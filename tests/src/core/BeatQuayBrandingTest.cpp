// SPDX-FileCopyrightText: 2026 Trieflow LLC
// SPDX-License-Identifier: GPL-2.0-or-later
#include <QtTest>
#include <QImage>
#include "BeatQuayIdentity.h"
#include "lmmsversion.h"
class BeatQuayBrandingTest : public QObject
{
    Q_OBJECT
private slots:
    void qtIdentityIsDistinctFromProjectSchema()
    {
        lmms::product::applyApplicationIdentity();
        QCOMPARE(QCoreApplication::applicationName(), QString("BeatSprig"));
        QCOMPARE(QCoreApplication::applicationVersion(), QString("1.0.1"));
        QCOMPARE(QCoreApplication::organizationName(), QString("Trieflow LLC"));
        QCOMPARE(QCoreApplication::organizationDomain(), QString("trieflow.com"));
        QCOMPARE(QString(lmms::product::DisplayTitle), QString("BeatSprig 1.0.1"));
        QVERIFY(QString(LMMS_VERSION).startsWith("1.3.0"));
        QCOMPARE(QString(lmms::product::Website), QString("https://beatsprig.trieflow.com"));
        QCOMPARE(QString(lmms::product::Privacy), QString("https://beatsprig.trieflow.com/privacy"));
        QCOMPARE(QString(lmms::product::Support), QString("https://beatsprig.trieflow.com/support"));
    }
    void actualEmbeddedOriginalIcon()
    {
        const QImage icon(lmms::product::Icon);
        QVERIFY(!icon.isNull());
        QCOMPARE(icon.size(), QSize(256, 256));
        QCOMPARE(icon.pixelColor(0, 0).alpha(), 0);
        QCOMPARE(icon.pixelColor(128, 20), QColor("#101b27"));
        QCOMPARE(icon.pixelColor(128, 48), QColor("#e5a4fa"));
        QCOMPARE(icon.pixelColor(128, 120), QColor("#edf4f4"));
    }
};
QTEST_GUILESS_MAIN(BeatQuayBrandingTest)
#include "BeatQuayBrandingTest.moc"
