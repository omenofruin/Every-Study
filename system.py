import sys
import os
import json
import random
import shutil
import zipfile
from datetime import datetime

try:
    from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                                 QLabel, QLineEdit, QPushButton, QListWidget, 
                                 QAbstractItemView, QMessageBox, QInputDialog, QFrame, 
                                 QSpinBox, QStackedWidget, QDialog, QScrollArea, QMainWindow, 
                                 QMenu, QFileDialog)
    from PyQt6.QtGui import QFont, QFontDatabase, QIcon, QAction
    from PyQt6.QtCore import Qt, QTimer
except ImportError:
    print("PyQt6가 설치되지 않았습니다. 'pip install PyQt6'를 실행하세요.")
    sys.exit(1)

# --- 오답 노트 회차 선택 및 보기 팝업 ---
class WrongNoteDialog(QDialog):
    def __init__(self, subject_name, subject_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"오답 노트 관리 - {subject_name}")
        self.resize(700, 800)
        self.setStyleSheet("background-color: #ede0d1;")
        self.subject_path = subject_path
        
        layout = QVBoxLayout(self)
        title = QLabel(f"[{subject_name}] 회차별 오답 기록")
        title.setStyleSheet("font-size: 20px; font-weight: 500; color: #5d4037; margin-bottom: 10px;")
        layout.addWidget(title)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet("background-color: white; border: none; height: 150px;")
        self.refresh_file_list()
        self.file_list.itemClicked.connect(self.display_note_content)
        layout.addWidget(QLabel("복습할 회차를 선택하세요:"))
        layout.addWidget(self.file_list)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: 2px solid #dccdbb; background-color: white;")
        
        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.content_container)
        layout.addWidget(self.scroll)
        
        btn_close = QPushButton("닫기")
        btn_close.setStyleSheet("background-color: #5d4037; color: white; padding: 10px; border: none;")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def refresh_file_list(self):
        self.file_list.clear()
        if os.path.exists(self.subject_path):
            files = sorted([f for f in os.listdir(self.subject_path) if f.startswith("오답노트_") and f.endswith(".txt")], reverse=True)
            self.file_list.addItems(files)

    def display_note_content(self, item):
        for i in reversed(range(self.content_layout.count())): 
            self.content_layout.itemAt(i).widget().setParent(None)
            
        file_path = os.path.join(self.subject_path, item.text())
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().split("-" * 50)
                for block in content:
                    if block.strip():
                        lbl = QLabel(block.strip())
                        lbl.setWordWrap(True)
                        lbl.setStyleSheet("padding: 15px; color: #333; border-bottom: 1px dashed #5d4037; font-size: 14px;")
                        self.content_layout.addWidget(lbl)

# --- 메인 윈도우 ---
class StudyMasterPyQt(QMainWindow):
    def __init__(self):
        super().__init__()
        
        if getattr(sys, 'frozen', False):
            self.current_path = os.path.dirname(sys.executable)
        else:
            self.current_path = os.path.dirname(os.path.abspath(__file__))
            
        self.base_dir = os.path.join(self.current_path, "study_subjects")
        self.font_dir = os.path.join(self.current_path, "fonts")
        self.icon_path = os.path.join(self.current_path, "icon.ico")
        
        if not os.path.exists(self.base_dir): os.makedirs(self.base_dir)
        if not os.path.exists(self.font_dir): os.makedirs(self.font_dir)

        self.current_subject = None
        self.question_bank = []
        
        self.init_font()
        self.init_ui()
        self.init_menu()
        self.refresh_subjects()

    def init_font(self):
        font_files = [f for f in os.listdir(self.font_dir) if f.endswith(('.ttf', '.otf'))]
        self.font_family = "Malgun Gothic"
        if font_files:
            font_path = os.path.join(self.font_dir, font_files[0])
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1: self.font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        self.main_font = QFont(self.font_family, 11)
        QApplication.setFont(self.main_font)

    def init_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet("background-color: #f5ece2; color: #5d4037;")
        data_menu = menubar.addMenu("데이터 관리")
        export_action = QAction("선택 과목 내보내기 (.zip)", self)
        export_action.triggered.connect(self.export_subject)
        data_menu.addAction(export_action)
        import_action = QAction("과목 가져오기 (.zip)", self)
        import_action.triggered.connect(self.import_subject)
        data_menu.addAction(import_action)
        data_menu.addSeparator()
        reset_action = QAction("선택 과목 기록 초기화 (오답/통계)", self)
        reset_action.triggered.connect(self.reset_subject_records)
        data_menu.addAction(reset_action)
        help_menu = menubar.addMenu("도움말")
        about_action = QAction("프로그램 정보", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def show_about(self):
        QMessageBox.about(self, "프로그램 정보", 
                          "모두의 스터디\n\n"
                          "효율적인 학습을 위한 모의고사 제작 및 공유 시스템\n\n"
                          "기획: 황보현우\n"
                          "제작 협력: Gemini (Google AI)\n\n"
                          "------------------------------------------\n"
                          "[ 라이선스 안내 ]\n"
                          "본 프로그램은 누구나 무료로 사용할 수 있으며,\n"
                          "자유로운 수정 및 업그레이드 배포가 가능합니다.\n\n"
                          "단, 본 프로그램 및 수정본을 유료로 판매하거나\n"
                          "상업적인 목적으로 이용하는 것을 엄격히 금지합니다.\n"
                          "------------------------------------------\n"
                          "2026. Hwangbo Hyun-woo. All rights reserved.")

    def init_ui(self):
        self.setWindowTitle("모두의 스터디")
        if os.path.exists(self.icon_path): self.setWindowIcon(QIcon(self.icon_path))
        self.resize(1100, 850)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #ede0d1;") 
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        btn_style = "QPushButton { background-color: #C0C0C0; border: none; padding: 10px; color: black; } QPushButton:pressed { background-color: #808080; color: white; }"
        input_style = "background-color: white; border: none; height: 35px; color: black; padding-left: 10px;"
        list_style = "background-color: white; border: none; color: black; padding: 5px;"
        left_side = QVBoxLayout()
        left_side.addWidget(QLabel("과목 폴더 목록", styleSheet="font-size: 15px; color: #5d4037;"))
        self.sub_list_widget = QListWidget()
        self.sub_list_widget.setStyleSheet(list_style)
        self.sub_list_widget.itemClicked.connect(self.on_subject_clicked)
        left_side.addWidget(self.sub_list_widget)
        btn_sub_lay = QVBoxLayout()
        btn_add_sub = QPushButton("과목 폴더 생성"); btn_add_sub.setStyleSheet(btn_style + "background-color: #000080; color: white;")
        btn_add_sub.clicked.connect(self.create_subject)
        btn_note = QPushButton("오답 노트 확인"); btn_note.setStyleSheet(btn_style + "background-color: #795548; color: white;")
        btn_note.clicked.connect(self.open_wrong_note_ui)
        btn_stats = QPushButton("시험 통계 확인"); btn_stats.setStyleSheet(btn_style + "background-color: #ff9800; color: white;")
        btn_stats.clicked.connect(self.show_statistics)
        btn_open_folder = QPushButton("전체 폴더 열기"); btn_open_folder.setStyleSheet(btn_style + "background-color: #5d4037; color: white;")
        btn_open_folder.clicked.connect(self.open_base_folder)
        btn_del_sub = QPushButton("과목 삭제"); btn_del_sub.setStyleSheet(btn_style + "color: #d32f2f;")
        btn_del_sub.clicked.connect(self.delete_current_subject)
        btn_sub_lay.addWidget(btn_add_sub); btn_sub_lay.addWidget(btn_note); btn_sub_lay.addWidget(btn_stats); btn_sub_lay.addWidget(btn_open_folder); btn_sub_lay.addWidget(btn_del_sub)
        left_side.addLayout(btn_sub_lay)
        main_layout.addLayout(left_side, 1)
        right_side = QVBoxLayout()
        self.lbl_status = QLabel("선택된 과목: 없음")
        self.lbl_status.setStyleSheet("background-color: #f5ece2; padding: 15px; font-size: 17px;")
        right_side.addWidget(self.lbl_status)
        reg_box = QFrame()
        reg_box.setStyleSheet("background-color: #dccdbb; border: none;")
        reg_lay = QVBoxLayout(reg_box)
        reg_lay.addWidget(QLabel("[ 문항 및 정답 등록 ]"))
        self.ent_q = QLineEdit(); self.ent_q.setPlaceholderText("문제 입력"); self.ent_q.setStyleSheet(input_style)
        self.ent_a = QLineEdit(); self.ent_a.setPlaceholderText("정답 입력"); self.ent_a.setStyleSheet(input_style)
        btn_reg = QPushButton("문제 등록"); btn_reg.setStyleSheet(btn_style + "background-color: #388e3c; color: white;")
        btn_reg.clicked.connect(self.add_question)
        reg_lay.addWidget(self.ent_q); reg_lay.addWidget(self.ent_a); reg_lay.addWidget(btn_reg)
        right_side.addWidget(reg_box)
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(list_style)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        right_side.addWidget(self.list_widget)
        btn_del_q = QPushButton("선택 항목 삭제"); btn_del_q.setStyleSheet(btn_style)
        btn_del_q.clicked.connect(self.delete_selected_questions)
        right_side.addWidget(btn_del_q)
        set_lay = QHBoxLayout()
        set_lay.addWidget(QLabel("시험 문항 수:"))
        self.spin_count = QSpinBox()
        self.spin_count.setStyleSheet("background-color: white; border: none; height: 30px;")
        self.spin_count.setRange(1, 999); self.spin_count.setValue(10)
        set_lay.addWidget(self.spin_count); set_lay.addStretch()
        right_side.addLayout(set_lay)
        self.btn_exam = QPushButton("시 험 시 작")
        self.btn_exam.setStyleSheet("background-color: #d32f2f; color: white; font-size: 22px; height: 70px; border: none;")
        self.btn_exam.clicked.connect(self.start_exam)
        right_side.addWidget(self.btn_exam)
        main_layout.addLayout(right_side, 2)

    def refresh_subjects(self):
        if not os.path.exists(self.base_dir): return
        subjects = sorted([d for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))])
        self.sub_list_widget.clear(); self.sub_list_widget.addItems(subjects)

    def on_subject_clicked(self, item): self.load_subject_data(item.text())

    def open_wrong_note_ui(self):
        if not self.current_subject: return
        subject_path = os.path.join(self.base_dir, self.current_subject)
        WrongNoteDialog(self.current_subject, subject_path, self).exec()

    def create_subject(self):
        name, ok = QInputDialog.getText(self, "과목 추가", "폴더명을 입력하세요:")
        if ok and name.strip():
            folder = os.path.join(self.base_dir, name.strip())
            if not os.path.exists(folder): os.makedirs(folder); self.refresh_subjects()

    def export_subject(self):
        if not self.current_subject: return
        save_path, _ = QFileDialog.getSaveFileName(self, "과목 내보내기", f"{self.current_subject}.zip", "Zip Files (*.zip)")
        if save_path:
            subject_path = os.path.join(self.base_dir, self.current_subject)
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(subject_path):
                    for file in files: zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(subject_path, '..')))
            QMessageBox.information(self, "성공", f"[{self.current_subject}] 과목 내보내기 완료.")

    def import_subject(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "과목 가져오기", "", "Zip Files (*.zip)")
        if file_path:
            with zipfile.ZipFile(file_path, 'r') as zipf: zipf.extractall(self.base_dir)
            self.refresh_subjects(); QMessageBox.information(self, "성공", "과목을 불러왔습니다.")

    def reset_subject_records(self):
        if not self.current_subject: return
        reply = QMessageBox.question(self, '기록 초기화', f"[{self.current_subject}]의 모든 통계 및 오답 노트를 삭제하시겠습니까?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            subject_path = os.path.join(self.base_dir, self.current_subject)
            stats_file = os.path.join(subject_path, "stats.json")
            if os.path.exists(stats_file): os.remove(stats_file)
            for file in os.listdir(subject_path):
                if file.startswith("오답노트_") and file.endswith(".txt"): os.remove(os.path.join(subject_path, file))
            QMessageBox.information(self, "완료", "기록이 초기화되었습니다.")

    def open_base_folder(self): os.startfile(self.base_dir)

    def delete_current_subject(self):
        if not self.current_subject: return
        if QMessageBox.question(self, '삭제', '영구 삭제하시겠습니까?', QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            shutil.rmtree(os.path.join(self.base_dir, self.current_subject))
            self.current_subject = None; self.refresh_subjects(); self.list_widget.clear()

    def load_subject_data(self, name):
        self.current_subject = name; self.lbl_status.setText(f"선택된 과목: {name}")
        file_path = os.path.join(self.base_dir, name, "questions.json")
        self.question_bank = []
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f: self.question_bank = json.load(f)
        self.update_list_view(); self.spin_count.setMaximum(max(1, len(self.question_bank)))

    def add_question(self):
        if not self.current_subject: return
        q, a = self.ent_q.text().strip(), self.ent_a.text().strip()
        if q and a:
            self.question_bank.append({"question": q, "answer": a}); self.save_bank()
            self.update_list_view(); self.ent_q.clear(); self.ent_a.clear(); self.spin_count.setMaximum(len(self.question_bank))

    def delete_selected_questions(self):
        indices = sorted([self.list_widget.row(i) for i in self.list_widget.selectedItems()], reverse=True)
        if indices and QMessageBox.question(self, '삭제', '삭제하시겠습니까?') == QMessageBox.StandardButton.Yes:
            for i in indices: self.question_bank.pop(i)
            self.save_bank(); self.update_list_view(); self.spin_count.setMaximum(max(1, len(self.question_bank)))

    def save_bank(self):
        path = os.path.join(self.base_dir, self.current_subject, "questions.json")
        with open(path, 'w', encoding='utf-8') as f: json.dump(self.question_bank, f, ensure_ascii=False, indent=4)

    def update_list_view(self):
        self.list_widget.clear()
        for it in self.question_bank: self.list_widget.addItem(f"Q: {it['question']} | A: {it['answer']}")

    def show_statistics(self):
        if not self.current_subject: return
        stats_path = os.path.join(self.base_dir, self.current_subject, "stats.json")
        if not os.path.exists(stats_path):
            QMessageBox.information(self, "통계", "기록이 없습니다.")
            return
        with open(stats_path, 'r', encoding='utf-8') as f: stats = json.load(f)
        stat_text = "\n".join([f"[{s['date']}] {s['score']}/{s['total']} ({s['percent']}%)" for s in stats[-10:]])
        QMessageBox.information(self, f"최근 통계 - {self.current_subject}", stat_text)

    def start_exam(self):
        if not self.question_bank: return
        self.ex = ExamWindow(self.question_bank, self.font_family, self.spin_count.value(), self.current_subject, self.icon_path, self.base_dir)
        self.ex.show()

# --- ExamWindow ---
class ExamWindow(QWidget):
    def __init__(self, data, font_name, count, sub_name, icon_path, base_dir):
        super().__init__()
        available_count = min(count, len(data))
        self.data = random.sample(data, available_count)
        self.font_name, self.sub_name, self.icon_path, self.base_dir = font_name, sub_name, icon_path, base_dir
        self.idx, self.score, self.wrong_records = 0, 0, []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"시험 진행 중 - {self.sub_name}")
        if os.path.exists(self.icon_path): self.setWindowIcon(QIcon(self.icon_path))
        self.setFixedSize(700, 600)
        self.setStyleSheet("background-color: #1a1a1a; color: white; border: none;")
        self.stack = QStackedWidget()
        self.page_exam = QWidget()
        exam_lay = QVBoxLayout(self.page_exam)
        self.lbl_q = QLabel(f"Q{self.idx+1}/{len(self.data)}: {self.data[0]['question']}")
        self.lbl_q.setStyleSheet("font-size: 20px; padding: 20px; background-color: #262626;")
        self.lbl_q.setAlignment(Qt.AlignmentFlag.AlignCenter); self.lbl_q.setWordWrap(True)
        self.ent = QLineEdit(); self.ent.setStyleSheet("font-size: 25px; color: #ffd600; background: #333; height: 50px;")
        self.ent.setAlignment(Qt.AlignmentFlag.AlignCenter); self.ent.returnPressed.connect(self.check)
        self.lbl_m = QLabel("정답 입력 후 엔터를 누르세요"); self.lbl_m.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_stop = QPushButton("시험 중단 (현재까지 점수 기록)"); btn_stop.setStyleSheet("background: #d32f2f; height: 40px;")
        btn_stop.clicked.connect(self.force_stop)
        exam_lay.addStretch(); exam_lay.addWidget(self.lbl_q); exam_lay.addWidget(self.ent); exam_lay.addWidget(self.lbl_m); exam_lay.addStretch(); exam_lay.addWidget(btn_stop)
        self.page_result = QWidget()
        res_lay = QVBoxLayout(self.page_result)
        self.lbl_res_title = QLabel("시험 종료"); self.lbl_res_title.setStyleSheet("font-size: 28px; color: #ffd600;")
        self.lbl_res_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_score = QLabel(""); self.lbl_score.setStyleSheet("font-size: 45px;")
        self.lbl_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_percent = QLabel(""); self.lbl_percent.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_close = QPushButton("결과 확인 완료"); btn_close.setStyleSheet("background: #388e3c; height: 60px; font-size: 18px;")
        btn_close.clicked.connect(self.close)
        res_lay.addStretch(); res_lay.addWidget(self.lbl_res_title); res_lay.addWidget(self.lbl_score); res_lay.addWidget(self.lbl_percent); res_lay.addStretch(); res_lay.addWidget(btn_close)
        self.stack.addWidget(self.page_exam); self.stack.addWidget(self.page_result)
        main_lay = QVBoxLayout(self); main_lay.addWidget(self.stack)

    def check(self):
        user_ans = self.ent.text().strip(); correct_ans = self.data[self.idx]['answer'].strip()
        if user_ans == correct_ans: 
            self.score += 1; self.lbl_m.setText("정답입니다."); self.lbl_m.setStyleSheet("color: #00c853;")
        else: 
            self.wrong_records.append({"q": self.data[self.idx]['question'], "user": user_ans if user_ans else "(미입력)", "correct": correct_ans})
            self.lbl_m.setText(f"오답! 정답: {correct_ans}"); self.lbl_m.setStyleSheet("color: #ff1744;")
        self.ent.setEnabled(False); QTimer.singleShot(1000, self.move)

    def move(self):
        self.idx += 1
        if self.idx < len(self.data):
            self.ent.setEnabled(True); self.ent.clear(); self.ent.setFocus()
            self.lbl_q.setText(f"Q{self.idx+1}/{len(self.data)}: {self.data[self.idx]['question']}")
            self.lbl_m.setText("다음 문제로..."); self.lbl_m.setStyleSheet("color: white;")
        else: self.show_result()

    def force_stop(self):
        reply = QMessageBox.question(self, '시험 중단', "시험을 중단하시겠습니까? 남은 문제는 모두 오답 처리됩니다.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            for i in range(self.idx, len(self.data)):
                if not any(w['q'] == self.data[i]['question'] for w in self.wrong_records):
                    self.wrong_records.append({"q": self.data[i]['question'], "user": "(시험 중단)", "correct": self.data[i]['answer']})
            self.show_result()

    def show_result(self):
        percent = round((self.score / len(self.data)) * 100, 1)
        self.lbl_score.setText(f"{self.score} / {len(self.data)}")
        self.lbl_percent.setText(f"최종 성취도: {percent}%")
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        stats_path = os.path.join(self.base_dir, self.sub_name, "stats.json")
        stats = []
        if os.path.exists(stats_path):
            with open(stats_path, 'r', encoding='utf-8') as f: stats = json.load(f)
        stats.append({"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "score": self.score, "total": len(self.data), "percent": percent})
        with open(stats_path, 'w', encoding='utf-8') as f: json.dump(stats, f, ensure_ascii=False, indent=4)
        if self.wrong_records:
            note_path = os.path.join(self.base_dir, self.sub_name, f"오답노트_{now}.txt")
            with open(note_path, "w", encoding="utf-8") as f:
                f.write(f"시험 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n결과: {self.score}/{len(self.data)} ({percent}%)\n" + "="*50 + "\n")
                for w in self.wrong_records: f.write(f"질문: {w['q']}\nㄴ 작성한 답: {w['user']}\nㄴ 정답: {w['correct']}\n" + "-"*50 + "\n")
        self.stack.setCurrentIndex(1)

if __name__ == "__main__":
    app = QApplication(sys.argv); win = StudyMasterPyQt(); win.show(); sys.exit(app.exec())