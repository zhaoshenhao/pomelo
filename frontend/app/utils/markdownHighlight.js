import { HighlightStyle } from "@codemirror/language";
import { tags } from "@lezer/highlight";

export const markdownHighlightStyle = HighlightStyle.define([
  { tag: tags.heading1, color: "#c62828", fontWeight: "bold" },
  { tag: tags.heading2, color: "#ad1457", fontWeight: "bold" },
  { tag: tags.heading3, color: "#5e35b1", fontWeight: "bold" },
  { tag: tags.heading4, color: "#1565c0", fontWeight: "bold" },
  { tag: tags.heading5, color: "#00573d", fontWeight: "bold" },
  { tag: tags.heading6, color: "#6d4c41", fontWeight: "bold" },
  { tag: tags.emphasis, color: "#1b5e20", fontStyle: "italic" },
  { tag: tags.strong, color: "#b71c1c", fontWeight: "bold" },
  { tag: tags.link, color: "#1565c0", textDecoration: "underline" },
  { tag: tags.url, color: "#0277bd", textDecoration: "underline" },
  { tag: tags.monospace, color: "#c7254e", backgroundColor: "#f5f2f0", borderRadius: "2px" },
  { tag: tags.quote, color: "#366d3a", fontStyle: "italic" },
  { tag: tags.list, color: "#5d4037" },
  { tag: tags.contentSeparator, color: "#9e9e9e" },
  { tag: tags.comment, color: "#80711e", fontStyle: "italic" },
  { tag: tags.strikethrough, textDecoration: "line-through", color: "#9e9e9e" },
  { tag: tags.meta, color: "#7b1fa2" }
]);
