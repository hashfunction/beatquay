// Copyright 2026 Trieflow LLC. MIT. Serialization fixture, not installed product evidence.
#include <QApplication>
#include <QDomDocument>
#include <QTextEdit>
#include <QTextStream>
#include <cstdio>
// DataFile constructor/write and ProjectNotes::saveSettings serialization route.
int main(int argc, char **argv) {
    QApplication app(argc, argv);
    QDomDocument doc("lmms-project");
    doc.appendChild(doc.createProcessingInstruction("xml", "version=\"1.0\""));
    auto root = doc.createElement("lmms-project");
    doc.appendChild(root);
    auto notes = doc.createElement("projectnotes");
    root.appendChild(notes);
    QTextEdit editor;
    notes.appendChild(doc.createCDATASection(editor.toHtml()));
    QTextStream output(stdout);
    doc.save(output, 2);
}
