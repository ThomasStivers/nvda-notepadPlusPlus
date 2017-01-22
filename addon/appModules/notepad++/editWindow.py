#editWindow.py
#A part of theNotepad++ addon for NVDA
#Copyright (C) 2016 Tuukka Ojala, Derek Riemer
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

import addonHandler
import config
from NVDAObjects.behaviors import EditableTextWithAutoSelectDetection
from editableText import EditableText
import api
from queueHandler import registerGeneratorObject
import speech
import textInfos
import tones
import ui
import eventHandler
import re
import locale

addonHandler.initTranslation()

class EditWindow(EditableTextWithAutoSelectDetection):
	"""An edit window that implements all of the scripts on the edit field for Notepad++"""

	def event_loseFocus(self):
		#Hack: finding the edit field from the foreground window is unreliable, so cache it here.
		self.appModule.edit = self

	def event_gainFocus(self):
		super(EditWindow, self).event_gainFocus()
		#Hack: finding the edit field from the foreground window is unreliable. If we previously cached an object, this will clean it up, allowing it to be garbage collected.
		self.appModule.edit = None

	def initOverlayClass(self):
		#Notepad++ names the edit window "N" for some stupid reason.
		#Nuke the name, because it really doesn't matter.
		self.name = ""

	def script_goToMatchingBrace(self, gesture):
		gesture.send()
		info = self.makeTextInfo(textInfos.POSITION_CARET).copy()
		#Expand to line.
		info.expand(textInfos.UNIT_LINE)
		if info.text.strip() in ('{', '}'):
			#This line is only one brace. Not very helpful to read, lets read the previous and next line as well.
			#Move it's start back a line.
			info.move(textInfos.UNIT_LINE, -1, endPoint = "start")
			# Move it's end one line, forward.
			info.move(textInfos.UNIT_LINE, 1, endPoint = "end")
			#speak the info.
			registerGeneratorObject((speech.speakMessage(i) for i in info.text.split("\n")))
		else:
			speech.speakMessage(info.text)

	#Translators: when pressed, goes to    the matching brace in Notepad++
	script_goToMatchingBrace.__doc__ = _("Goes to the brace that matches the one under the caret")
	script_goToMatchingBrace.category = "Notepad++"

	def script_goToNextBookmark(self, gesture):
		self.speakActiveLineIfChanged(gesture)

	#Translators: Script to move to the next bookmark in Notepad++.
	script_goToNextBookmark.__doc__ = _("Goes to the next bookmark")
	script_goToNextBookmark.category = "Notepad++"

	def script_goToPreviousBookmark(self, gesture):
		self.speakActiveLineIfChanged(gesture)

	#Translators: Script to move to the next bookmark in Notepad++.
	script_goToPreviousBookmark.__doc__ = _("Goes to the previous bookmark")
	script_goToPreviousBookmark.category = "Notepad++"

	def speakActiveLineIfChanged(self, gesture):
		old = self.makeTextInfo(textInfos.POSITION_CARET)
		gesture.send()
		new = self.makeTextInfo(textInfos.POSITION_CARET)
		if new.bookmark.startOffset != old.bookmark.startOffset:
			new.expand(textInfos.UNIT_LINE)
			speech.speakMessage(new.text)

	def event_typedCharacter(self, ch):
		super(EditWindow, self).event_typedCharacter(ch)
		if not config.conf["notepadPp"]["lineLengthIndicator"]:
			return
		textInfo = self.makeTextInfo(textInfos.POSITION_CARET)
		textInfo.expand(textInfos.UNIT_LINE)
		if textInfo.bookmark.endOffset - textInfo.bookmark.startOffset >= config.conf["notepadPp"]["maxLineLength"]:
			tones.beep(500, 50)

	def script_reportLineOverflow(self, gesture):
		if self.appModule.isAutocomplete:
			gesture.send()
			return
		self.script_caret_moveByLine(gesture)
		if not config.conf["notepadPp"]["lineLengthIndicator"]:
			return
		info = self.makeTextInfo(textInfos.POSITION_CARET)
		info.expand(textInfos.UNIT_LINE)
		if len(info.text.strip('\r\n\t ')) > config.conf["notepadPp"]["maxLineLength"]:
			tones.beep(500, 50)

	def event_caret(self):
		super(EditWindow, self).event_caret()
		if not config.conf["notepadPp"]["lineLengthIndicator"]:
			return
		caretInfo = self.makeTextInfo(textInfos.POSITION_CARET)
		lineStartInfo = self.makeTextInfo(textInfos.POSITION_CARET).copy()
		caretInfo.expand(textInfos.UNIT_CHARACTER)
		lineStartInfo.expand(textInfos.UNIT_LINE)
		caretPosition = caretInfo.bookmark.startOffset -lineStartInfo.bookmark.startOffset
		#Is it not a blank line, and are we further in the line than the marker position?
		if caretPosition > config.conf["notepadPp"]["maxLineLength"] -1 and caretInfo.text not in ['\r', '\n']:
			tones.beep(500, 50)

	def script_goToFirstOverflowingCharacter(self, gesture):
		info = self.makeTextInfo(textInfos.POSITION_CARET)
		info.expand(textInfos.UNIT_LINE)
		if len(info.text) > config.conf["notepadPp"]["maxLineLength"]:
			info.move(textInfos.UNIT_CHARACTER, config.conf["notepadPp"]["maxLineLength"], "start")
			info.updateCaret()
			info.collapse()
			info.expand(textInfos.UNIT_CHARACTER)
			speech.speakMessage(info.text)

	#Translators: Script to move the cursor to the first character on the current line that exceeds the users maximum allowed line length.
	script_goToFirstOverflowingCharacter.__doc__ = _("Moves to the first character that is after the maximum line length")
	script_goToFirstOverflowingCharacter.category = "Notepad++"

	lineInfoExpression = re.compile(r"^Ln\D+(\d\w*)\D+(\d\w*)\D+(\d\w*)\D+(\d\w*)")
	def script_reportLineInfo(self, gesture):
		lineInfo = self.parent.next.next.firstChild.getChild(2).name
		# Get only the numbers we want from the statusBar.
		lines, columns, selectedCharacters, selectedLines = self.lineInfoExpression.match(lineInfo).groups()
		#Translators: The line and column position of the cursor.
		lineInfo = _("line %s column %s" % (lines, columns))
		if (locale.atoi(selectedCharacters)):	# Test the number not the string.
			#Translators: The number of characters selected.
			lineInfo += _(" %s characters selected" % (selectedCharacters))
			if (locale.atoi(selectedLines)):	# Test the number not the string.
				#Translators: The number of lines selected.
				lineInfo += _(" %s lines selected" % (selectedLines))
		ui.message(lineInfo)

	#Translators: Script that announces information about the current line.
	script_reportLineInfo.__doc__ = _("speak the line info item on the status bar")
	script_reportLineInfo.category = "Notepad++"

	def script_reportFindResult(self, gesture):
		old = self.makeTextInfo(textInfos.POSITION_SELECTION)
		gesture.send()
		new = self.makeTextInfo(textInfos.POSITION_SELECTION)
		if new.bookmark.startOffset != old.bookmark.startOffset:
			new.expand(textInfos.UNIT_LINE)
			speech.speakMessage(new.text)
		else:
			#Translators: Message shown when there are no more search results in this direction using the notepad++ find command.
			speech.speakMessage(_("No more search results in this direction."))

	#Translators: when pressed, goes to    the Next search result in Notepad++
	script_reportFindResult.__doc__ = _("Queries the next or previous search result and speaks the selection and current line of it.")
	script_reportFindResult.category = "Notepad++"

	__gestures = {
		"kb:control+b" : "goToMatchingBrace",
		"kb:f2": "goToNextBookmark",
		"kb:shift+f2": "goToPreviousBookmark",
		"kb:nvda+shift+\\": "reportLineInfo",
		"kb:upArrow": "reportLineOverflow",
		"kb:downArrow": "reportLineOverflow",
		"kb:nvda+g": "goToFirstOverflowingCharacter",
		"kb:f3" : "reportFindResult",
		"kb:shift+f3" : "reportFindResult",
	}
