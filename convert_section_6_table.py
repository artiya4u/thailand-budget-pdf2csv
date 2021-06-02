import csv
import glob
import os
import re

# sudo apt install poppler-utils

year = '2565'

project_title_prefix = ('ผลผลิต', 'แผนงาน', 'โครงการ', 'ครงการ', 'แ นงาน')
org_prefix = ['กระทรวง', 'สานัก', 'องค์กรปกครอง', 'จังหวัดและก', 'รัฐวิสา', 'หน่ วยงาน', 'ส่วนราชการ', 'สภา']
org_prefix = [(' ' * 30) + x for x in org_prefix]  # Add spaces to know organization name in center of the page
section_6_2_prefix = [
    '6.2 จาแนกตามแผนงาน ผลผลิต/โครงการ และงบรายจ่าย',
    '6.2 จําแนกตามแผนงาน ผลผลิต/โครงการ และงบรายจ่าย',
    f'6. สรุปงบประมาณรายจ่ายประจาปี งบประมาณ พ.ศ. {year} จาแนกตามแผนงาน ผลผลิต/โครงการ และงบรายจ่าย',
    '6.2 า'
]

specials = ['ุ', 'ู', 'ึ', 'ำ', 'ั', 'ี', '้', '็', '่', '๋']


def fix_align(txt):
    input_txt = list(txt)
    result = list('')
    skip_next = False
    for idx, val in enumerate(input_txt):
        if val in specials and idx > 1 and idx + 1 < len(input_txt) and input_txt[idx + 1] == ' ':
            temp = result.pop()
            result.append(val)
            result.append(temp)
            skip_next = True
        else:
            if not skip_next:
                result.append(val)
            skip_next = False

    return ''.join(result)


def thai_number_to_arabic(thai_number):
    thai_number = thai_number.replace('๐', '0')
    thai_number = thai_number.replace('๑', '1')
    thai_number = thai_number.replace('๒', '2')
    thai_number = thai_number.replace('๓', '3')
    thai_number = thai_number.replace('๔', '4')
    thai_number = thai_number.replace('๕', '5')
    thai_number = thai_number.replace('๖', '6')
    thai_number = thai_number.replace('๗', '7')
    thai_number = thai_number.replace('๘', '8')
    thai_number = thai_number.replace('๙', '9')
    thai_number = thai_number.replace(',', '')
    return thai_number


def replace_dash(text):
    if text == '-':
        return '0'
    else:
        return text


def convert_table_6(pdf_budget_file):
    print(f'Start convert file: {pdf_budget_file}')
    os.system(f'pdftotext -layout {pdf_budget_file}')
    text_file_name = pdf_budget_file.replace('.pdf', '.txt')
    project_budgets = []
    with open(text_file_name) as text_file:
        book_year = 0
        issue_num = 0
        book_num = 0
        sub_book_num = 0
        item_num = 0
        page = 0
        count = 0
        lines = text_file.readlines()
        is_section_6 = False
        is_row = False
        org_name = None
        sub_org_name = None
        project_name = ''
        personnel_budget = 0
        operational_budget = 0
        investing_budget = 0
        subsidy_budget = 0
        other_budget = 0
        sum_budget = None
        for line in lines:
            count += 1
            if any(line.find(x) > 0 for x in org_prefix) and lines[count].strip() != '':
                org_name = line.strip()
                sub_org_name = lines[count].strip()

            if line.find('เอกสารงบประมาณ ฉ') > 0:
                line = thai_number_to_arabic(line)
                numbers = re.findall('[0-9]+', line)
                if len(numbers) > 0:
                    issue_num = numbers[0]

            if line.startswith('ประจ') and line.find('งบประมาณ พ.ศ.') > 0:
                line = thai_number_to_arabic(line)
                numbers = re.findall('[0-9]+', line)
                if len(numbers) > 0:
                    book_year = int(numbers[0]) - 543

            if line.find('เล่มท') > 0:
                line = thai_number_to_arabic(line)
                numbers = re.findall('[0-9]+', line)
                if len(numbers) == 2:
                    book_num = numbers[1]
                    sub_book_num = numbers[0]

            # ignore page number.
            if line.startswith(''):
                try:
                    num = int(line.strip())
                    if num > page:
                        page = num
                except ValueError:
                    pass
                continue

            segments = line.split('  ')
            segments = list(filter(lambda x: x != '', segments))
            segments = list(map(str.strip, segments))
            segments = list(map(fix_align, segments))
            segments = list(map(replace_dash, segments))

            # Condition find for section 6.2
            if any(line.startswith(x) for x in section_6_2_prefix):
                is_section_6 = True
                continue

            # Inside 6.2 section loop fill all value
            if line.startswith('รวม') and is_section_6:
                is_row = True
                continue

            if is_section_6 and is_row:
                no_number_title = re.sub(r'\d\.', '', segments[0]).strip()
                if no_number_title.startswith(project_title_prefix) \
                        or segments[0].find('7. รายละเอียดงบประมาณจ') >= 0:
                    if project_name != '' and sum_budget is not None and sum_budget != 'รวม':
                        is_plan = re.search(r'\d\.', project_name) is not None
                        cross_func = project_name.find('แผนงานบูรณาการ') > 0
                        item_num += 1
                        ref_doc = f'{book_year}.{issue_num}.{book_num}.{sub_book_num}'
                        item_id = f'{ref_doc}.{item_num}'
                        plan = {
                            'ITEM_ID': item_id,
                            'REF_DOC': ref_doc,
                            'REF_PAGE_NO': page,
                            'MINISTRY': org_name,
                            'BUDGETARY_UNIT': sub_org_name,
                            'CROSS_FUNC': cross_func,
                            'PROJECT': project_name,
                            'is_plan': is_plan,
                            'personnel_budget': personnel_budget,
                            'operational_budget': operational_budget,
                            'investing_budget': investing_budget,
                            'subsidy_budget': subsidy_budget,
                            'other_budget': other_budget,
                            'sum_budget': sum_budget,
                        }
                        print(plan)
                        project_budgets.append(plan)
                        project_name = ''
                        sum_budget = None

                if segments[0].find('7. รายละเอียดงบประมาณจ') >= 0:
                    is_row = False
                    is_section_6 = False
                    sum_budget = None
                    continue

                if no_number_title.startswith(project_title_prefix):
                    project_name = segments[0]
                else:
                    project_name += segments[0]
                if len(segments) == 7:
                    personnel_budget = segments[1]
                    operational_budget = segments[2]
                    investing_budget = segments[3]
                    subsidy_budget = segments[4]
                    other_budget = segments[5]
                    sum_budget = segments[6]

    if len(project_budgets) > 0:
        try:
            os.makedirs('budget-csv/')
        except OSError:
            pass
        csv_file_name = 'budget-csv/' + pdf_budget_file.split('/')[1].replace('.pdf', '.csv')
        f = open(csv_file_name, 'w')
        w = csv.DictWriter(f, project_budgets[0].keys())
        w.writeheader()
        w.writerows(project_budgets)
        f.close()


if __name__ == '__main__':
    pdf_path = 'budget-pdf/'
    list_of_files = sorted(filter(os.path.isfile, glob.glob(pdf_path + '*.pdf')))
    for file in list_of_files:
        if file.endswith('.pdf'):
            convert_table_6(file)
