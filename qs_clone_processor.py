import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import pickle
import time
from pathlib import Path
from collections import OrderedDict
from subprocess import Popen, PIPE
import os, sys, traceback
import glob2
import matplotlib.pyplot as plt
from statistics import mean, median
from datetime import datetime
from dateutil import relativedelta


def write_file(filename, fcontent, mode, isprint):
    """
    Write the string content to a file
    copied from
    http://www.pythonforbeginners.com/files/reading-and-writing-files-in-python
    :param filename: name of the file
    :param fcontent: string content to put into the file
    :param mode: writing mode, 'w' overwrite every time, 'a' append to an existing file
    :return: N/A
    """
    # try:
    file = open(filename, mode)
    file.write(fcontent)
    file.close()

    if isprint:
        print("saved:" + filename)


def delete_file(filename):
    """ delete the file and recreate it
    :param filename: the name of file
    :return: True = succeeded, False = failed
    """
    try:
        os.remove(filename)
    except OSError:
        return False

    return True


def connect_firebase():
    # Fetch the service account key JSON file contents
    cred = credentials.Certificate('cloverflow-exqs-outdated-firebase-adminsdk.json')

    # Initialize the app with a service account, granting admin privileges
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://cloverflow-exqs-outdated.firebaseio.com'
    })
    # Get a database reference to our clone pairs.
    ref = db.reference('clones/pairs')

    return ref


def download_clones():
    ref = connect_firebase()
    # download all clone pairs
    clones = ref.get()
    # for idx, clone in enumerate(clones):
    #     if clone is None:
    #         del clones[idx]
    print("total clone pairs from the firebase db: ", len(clones))
    return clones


def clean(clones):
    print('removing null clone pairs.')
    filtered = []
    for idx, c in enumerate(clones):
        if c is not None:
            filtered.append(c)
        else:
            print('removed: ', idx)
    return filtered


def write_clones_to_file(clones, columns, file_name, print_header=True, quote_on=False):
    # clones = download_clones()
    delete_file(file_name)
    # write to a csv file
    content = ""

    if print_header:
        for idx, c in enumerate(columns):
            if idx < len(columns) - 1:
                content += c + ","
            else:
                content += c + "\n"

    if quote_on:
        quote = "\""
    else:
        quote = ""

    for idx, clone in enumerate(clones):
        for j, column in enumerate(columns):
            if j != len(columns) - 1:
                content += quote + str(clone[column]) + quote + ","
            else:
                content += quote + str(clone[column]) + quote + "\n"

    write_file(file_name, content, "w", True)


def print_a_clone(clone, columns, print_header=True):
    content = ""

    for j, column in enumerate(columns):
        if print_header:
            content += column + '='

        if column is 'latest_change_date':
            s, ms = divmod(int(clone[column]), 1000)
            content += '%s.%03d' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(s)), ms) + ','
        else:
            content += str(clone[column]) + ','

    print(content)


def print_latex(clone, columns, print_header=True):
    content = ""
    if print_header:
        for column in columns:
            content += column + ' & '
        content += ' \\\\ '

    for j, column in enumerate(columns):

        if column is 'latest_change_date':
            s, ms = divmod(int(clone[column]), 1000)
            content += '%s.%03d' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(s)), ms) + '\n'
        else:
            content += str(clone[column]) + ' & '
        content += ' \\\\\n'

    print(content)


def snippet_in_list(snippets, c):
    found = False;
    for snippet in snippets:
        if c["file1"].strip() == snippet["file1"].strip():
            # already exist
            found = True
            return found

    return found


def clone_in_list(clones, c):
    found = False;
    for clone in clones:
        if c["file1"].strip() == clone["file1"].strip() \
                and c["start1"] == clone["start1"] \
                and c["end1"] == clone["end1"]:
            # already exist
            found = True
            return found

    return found


def get_unique_so_snippets(clones):
    all_snippets = []
    u_snippets = []
    for idx, clone in enumerate(clones):
        all_snippets.append(clone)
        if not snippet_in_list(u_snippets, clone):
            u_snippets.append(clone)

    return u_snippets, all_snippets


def get_unique_so_snippets_with_filter(clones, selected_field, selected_value):
    u_snippets = []
    for idx, clone in enumerate(clones):
        # filter unwanted clone pairs
        if clone[selected_field] == selected_value:
            if not snippet_in_list(u_snippets, clone):
                u_snippets.append(clone)

    return u_snippets


def get_unique_so_clones_with_filter(clones, selected_field, selected_value):
    allclones = []
    uclones = []
    for idx, clone in enumerate(clones):
        # filter unwanted clone pairs
        if clone[selected_field] == selected_value:
            allclones.append(clone)
            if not clone_in_list(uclones, clone):
                uclones.append(clone)

    return uclones, allclones


def get_unique_so_clones_keyword(clones, selected_field, selected_value):
    allclones = []
    uclones = []
    for idx, clone in enumerate(clones):
        # filter unwanted clone pairs
        if selected_value in clone[selected_field]:
            allclones.append(clone)
            if not clone_in_list(uclones, clone):
                uclones.append(clone)

    return uclones, allclones


def get_unique_so_clones(clones):
    uclones = []
    for idx, clone in enumerate(clones):
        if not clone_in_list(uclones, clone):
            uclones.append(clone)

    return uclones


def get_outdated_clones(clones):
    outdated_clones = []
    for clone in clones:
        if clone["latest_ischanged"] == "true":
            outdated_clones.append(clone)

    return outdated_clones


def get_projects_having_outdated_clones(clones):
    projs_dict = dict()
    for clone in clones:
        if clone["latest_ischanged"] == "true":
            proj = format_project_name(clone['file2'].split('/')[0])
            if proj not in projs_dict:
                projs_dict[proj] = 1
            else:
                projs_dict[proj] += 1

    return projs_dict


def get_code_mod_types(clones):
    mod_types = {
            'latest_change_ad': 0,
            'latest_change_md': 0,
            'latest_change_rm': 0,
            'latest_change_rw': 0,
            'latest_change_ap': 0,
            'latest_deleted': 0
        }
    for clone in clones:
        mod_types['latest_change_ad'] += clone['latest_change_ad']
        mod_types['latest_change_md'] += clone['latest_change_md']
        mod_types['latest_change_rm'] += clone['latest_change_rm']
        mod_types['latest_change_rw'] += clone['latest_change_rw']
        mod_types['latest_change_ap'] += clone['latest_change_ap']
        mod_types['latest_deleted'] += clone['latest_deleted']

    return mod_types


def get_outdated_with_issues(clones):
    issues_clones = []
    for clone in clones:
        if clone["latest_ischanged"] == "true" \
                and clone["latest_note"].startswith("@"):
            issues_clones.append(clone)

    return issues_clones


def get_qproject(clones):
    projects = []
    count = []
    for clone in clones:
        proj_name = clone['file2'].split('/')[0]
        if proj_name not in projects:
            projects.append(proj_name)
            count.append(1)
        else:
            idx = projects.index(proj_name)
            count[idx] += 1
    return projects, count


# copied from
# https://stackoverflow.com/questions/17225287/python-2-7-write-and-read-a-list-from-file
def write_list_to_file(list, file):
    with open(file, 'wb') as f:
        pickle.dump(list, f)
    print("save list to file: " + file)


# copied from
# https://stackoverflow.com/questions/17225287/python-2-7-write-and-read-a-list-from-file
def read_list_from_file(file):
    with open(file, 'rb') as f:
        list = pickle.load(f)

    return list


def plot_clone_size(clones):
    sizes = []
    for clone in clones:
        start = clone['start1']
        end = clone['end1']
        size = end - start + 1
        size.append(size)



def get_numlines(code):
    lines = code.strip().split('\n')
    return len(lines)


def get_clone_ratio(clone, field_index):
    code_field = "code" + str(field_index)
    start_field = "start" + str(field_index)
    end_field = "end" + str(field_index)

    size = get_numlines(clone[code_field])
    # print(clone[start_field], clone[end_field])
    clone_size = clone[end_field] - clone[start_field] + 1
    # print(size, clone_size)
    return clone_size/size


def get_avg_clone_ratio(clones, field_index):
    total = 0
    for clone in clones:
        ratio = get_clone_ratio(clone, field_index)
        total += ratio
    return total/len(clones)


def format_project_name(name):
    return name.replace("apache-", "").replace("_", "-").split('-')[0].lower()


def plot_outdated(projects):
    import matplotlib
    import matplotlib.pyplot as plt;
    plt.rcdefaults()
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.figure as figure
    from matplotlib.backends.backend_pdf import PdfPages
    matplotlib.rcParams.update({'font.size': 16})

    keys = list(projects.keys())
    y_pos = np.arange(len(keys))
    values = list(projects.values())

    fig, ax = plt.subplots()
    plt.bar(y_pos, values, align='center')
    plt.xticks(y_pos, keys)
    plt.ylabel('Pairs')
    labels = ax.get_xticklabels()
    plt.yticks(np.arange(min(values), max(values) + 1, 3.0))
    plt.setp(labels, rotation=30, ha='right')
    fig.tight_layout()
    # plt.show()

    pp = PdfPages('outdated.pdf')
    fig.set_size_inches(12, 4)
    pp.savefig(fig)
    pp.close()


def plot_mod_types(mod_types):
    import matplotlib
    import matplotlib.pyplot as plt;
    plt.rcdefaults()
    import numpy as np
    import matplotlib.pyplot as plt
    import matplotlib.figure as figure
    from matplotlib.backends.backend_pdf import PdfPages
    matplotlib.rcParams.update({'font.size': 16})

    keys = [ 'Stmt. addition', 'Stmt. modification', 'Stmt. removal', 'method rewriting', 'API change', 'file deletion' ]
    y_pos = np.arange(len(keys))
    values = list(mod_types.values())

    fig, ax = plt.subplots()
    plt.bar(y_pos, values, align='center')
    plt.xticks(y_pos, keys)
    plt.ylabel('Pairs')
    labels = ax.get_xticklabels()
    # plt.yticks(np.arange(min(values), max(values) + 1, 1.0))
    plt.setp(labels, rotation=30, ha='right')
    fig.tight_layout()
    # plt.show()

    pp = PdfPages('mod_types.pdf')
    fig.set_size_inches(6, 6)
    pp.savefig(fig)
    pp.close()


def get_license(classification, clones):
    licenses = dict()
    column1 = 'code1_license'
    column2 = 'code2_license'
    if classification == "EX":
        column1 = 'code1_license'
        column2 = 'ex_license'
    for idx, clone in enumerate(clones):
        write_file('clone_licenses.csv',
                   classification + ',' +
                   clone['file1'] + ',' + clone['file2'] + ',' +
                   clone[column1] + ',' + clone[column2] + '\n',
                   'a', False)
        key = clone[column1] + " & " + clone[column2]
        if key not in licenses.keys():
            licenses[key] = 1
        else:
            licenses[key] += 1

    return licenses


def update_license(classification, clones):
    ref = connect_firebase()
    count = 0
    for idx, clone in enumerate(clones):
        if clone['classification'] == classification:
            count += 1
            fileloc = '/Users/Chaiyong/Downloads/stackoverflow/stackoverflow_orig/' + clone['file1']
            solicense = run_ninka(fileloc).split(';')[1].replace('\\n\'', '').replace(',', '/')
            solicense = solicense.replace('NONE', 'No license')

            fileloc = '/Users/Chaiyong/Downloads/stackoverflow/QualitasCorpus-20130901r/projects_orig_130901/' + clone[
                'file2']
            qlicense = run_ninka(fileloc).split(';')[1].replace('\\n\'', '').replace(',', '/')
            qlicense = qlicense.replace('NONE', 'No license')

            # add license to the clone pair
            pairs_ref = ref.child(str(idx))
            pairs_ref.update({
                'code1_license': solicense,
                'code2_license': qlicense
            })
            print(count, 'done updating id', idx)


def run_ninka(file):
    p = Popen(["/Users/Chaiyong/Downloads/stackoverflow/tools/ninka-1.3/ninka.pl", "-d", file], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()
    return str(output).strip()


def get_file_size(location):
    filesizes = []
    """ Get all javascript files in a folder recursively """
    javafiles = glob2.glob(location + '/**/*.java')
    for idx, file in enumerate(javafiles):
        with open(file, 'r') as myfile:
            size = len(myfile.read().strip().split('\n'))
            # print(idx, file, size)
            filesizes.append(size)

    return filesizes


def create_csv(clones):
    columns = ['file1', 'start1', 'end1', 'file2', 'start2', 'end2', 'classification', 'notes']
    write_clones_to_file(clones, columns, "clones.csv", print_header=True, quote_on=True)


def stats(data):
    print(min(data), '&', max(data), '&', mean(data), '&', median(data), '\\\\')


def get_sizes(data):
    return [d['end1'] - d['start1'] + 1 for d in data]


def boxplot(data1, data2, data3, data4, data5, data6):
    """
    Plot a boxplot of clone size (QS, UD, EX)
    :param data1: clones#1 (QS)
    :param data2: clones#2 (UD)
    :param data3: clones#3 (EX)
    :return: N/A
    """
    size1 = get_sizes(data1)
    size2 = get_sizes(data2)
    size3 = get_sizes(data3)
    size4 = get_sizes(data4)
    size5 = get_sizes(data5)
    size6 = get_sizes(data6)
    data = [size1, size2, size3, size4, size5, size6]
    plt.figure()
    plt.boxplot(data)
    # plt.ylim(10)
    plt.ylabel('no. of lines')
    plt.xticks([1, 2, 3, 4, 5, 6], ['QS', 'SQ', 'UD', 'EX', 'BP', 'IN'])
    plt.savefig('boxplot_clone_size.pdf', bbox_inches='tight')


def boxplot_combined(data1, data2, data3, data4, data5, data6):
    """
    Plot a boxplot of clone size (QS, UD, EX)
    :param data1: clones#1 (QS)
    :param data2: clones#2 (SQ)
    :param data3: clones#3 (UD)
    :param data4: clones#4 (EX)
    :return: N/A
    """
    combined = data1 + data2 + data3 + data4 + data5 + data6
    size = get_sizes(combined)
    data = [size]
    fig = plt.figure()
    plt.boxplot(data, vert=False)
    # plt.ylim(10)
    plt.xlabel('no. of lines')
    plt.xlim(0, 140)
    plt.tick_params(
        axis='y',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        left=False,  # ticks along the bottom edge are off
        right=False,  # ticks along the top edge are off
        labelleft=False)  # labels along the bottom edge are off
    fig.set_size_inches(7, 2)
    plt.savefig('boxplot_clone_size_combined.pdf', bbox_inches='tight')


def write_outdated_clones_to_file(outdated_clones):
    metadata = ''
    # write all the outdated snippets to files
    for i, oc in enumerate(outdated_clones):
        lines = oc['code1'].split('\n')
        # print(oc['file1'], oc['start1'], oc['end1'])
        code = '\n'.join(lines[int(oc['start1']) - 1: int(oc['end1'])])
        # print(oc)
        # print_a_clone(oc, ['file1', 'code1'], print_header=False)
        metadata += str(i + 1) + '_' + oc['file1'] + ',' + str(oc['start1']) + ',' + str(oc['end1']) + ','
        metadata += oc['file2'] + ',' + str(oc['start2']) + ',' + str(oc['end2']) + '\n'
        write_file(
            '/Users/Chaiyong/Downloads/stackoverflow/stackoverflow_outdated_snippets/' + str(i + 1) + '_' + oc['file1'],
            code, 'w', False)
    write_file('outdated_metadata.csv', metadata, 'w', False)


def count_od_comment_outdated(outdated_clones):
    count = [0, 0, 0]
    changed = 0
    for idx, odc in enumerate(outdated_clones):
        if odc['od_comment_outdated'] == 'Yes' or odc['od_comment_outdated'] == 'Maybe':
            count[0] += 1
            if odc['od_changed_outdated_code'] == 'Yes':
                changed += 1
        elif odc['od_comment_outdated'] == 'No':
            count[1] += 1
        elif odc['od_comment_outdated'] == 'Not found':
            count[2] += 1
    return count, changed


def count_newer_higher_votes(outdated_clones):
    newer_count = 0
    higher_vote_count = [0, 0]
    for idx, odc in enumerate(outdated_clones):
        if 'Yes' in odc['od_newer_answer']:
            newer_count += 1
        if 'Yes' in odc['od_higher-voted_answers']:
            higher_vote_count[0] += 1
        elif 'Equal' in odc['od_higher-voted_answers']:
            higher_vote_count[1] += 1
    return newer_count, higher_vote_count


def get_clone_ages(clones, type, ref_dates):
    data = list()
    for idx, odc in enumerate(clones):
        if odc['od_answer_post_date'] != 'None':
            postdate = odc['od_answer_post_date'].split(' ')[0]
            d = datetime.strptime(postdate, '%d-%b-%y')
            proj_name = odc['file2'].split('/')[0]
            ref_d = datetime.strptime(ref_dates[proj_name], '%d-%b-%y')
            # exit()
            if type == 'days':
                delta = d - ref_d
                data.append(delta.days)
            elif type == 'months':
                r = relativedelta.relativedelta(d, ref_d)
                if r.years < 0:
                    r.years = 0
                if r.months < 0:
                    r.months = 0
                # print(d, ref_d, r.years, r.months)
                data.append(r.years * 12 + r.months)
            else:
                print('Error: wrong clone age type (days or months).')
                exit()
    return data


def get_qs_ref_dates():
    ref_dates = {
        'antlr4-4.0': '22-Jan-13',
        'apache-ant-1.8.4': '23-May-12',
        'apache-log4j-1.2.16': '31-Mar-10',
        'apache-tomcat-7.0.2': '11-Aug-10',
        'Compiere_330_Source': '2-Mar-09',
        'eclipse_SDK': '5-Jun-13',
        'hadoop-1': '27-Dec-11',
        'hibernate-release-4': '22-May-13',
        'iReport-3': '22-Sep-10',
        'iText-src-5': '22-Jul-10',
        'jasperreports-3': '1-Jun-10',
        'jfreechart-1': '20-Apr-09',
        'jgraph-latest-bsd-src': '23-Nov-09',
        'jgrapht-0': '11-Mar-11',
        'jstock-1.0.7c': '18-Jun-13',
        'jung2-2_0_1': '25-Jan-10',
        'junit-4': '14-Nov-12',
        'lucene-4.3.0': '3-May-13',
        'netbeans-6.9.1-201007282301': '28-Jul-10',
        'poi-3.6-20091214': '14-Dec-09',
        'spring-framework-3.0.5': '29-Oct-10',
        'struts2-2.2.1-all': '15-Aug-10',
        'weka-3-7-9': '21-Feb-13',
        'c-jdbc-2': '2-Jan-13',
        'jboss-5': '23-May-09',
        'freemind-src-0': '18-Feb-11',
        'geotools-2': '2-Sep-10',
        'aoisrc281': '15-Feb-10'
    }
    return ref_dates


def boxplot_post_age(clone_set, names):
    plt.figure()
    type = 'months'
    ref_dates = get_qs_ref_dates()
    data = list()
    for set in clone_set:
        data.append(get_clone_ages(set, type, ref_dates))
    print('\nCLONE AGE (' + type + ')')
    print('min & max & mean & median')
    for idx, name in enumerate(names):
        print(name, end=' & ')
        stats(data[idx])

    fig = plt.figure()
    plt.boxplot(data, vert=False)
    # plt.xticks(range(1, len(names) + 1), names)
    plt.xlabel('age of clones (' + type + ')')
    plt.tick_params(
        axis='y',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        left=False,  # ticks along the bottom edge are off
        right=False,  # ticks along the top edge are off
        labelleft=False)  # labels along the bottom edge are off
    fig.set_size_inches(7, 2)
    plt.savefig('boxplot_clone_age.pdf', bbox_inches='tight')


def count_outdated_reason(outdated_clones):
    reasons = dict()
    for idx, odc in enumerate(outdated_clones):
        r = odc['od_reason_change']
        if r not in reasons:
            reasons[r] = 1
        else:
            reasons[r] = reasons[r] + 1
        # if r == 'bug':
        #     print(odc['file1'])
    return reasons


def print_no_date_clones(clones):
    for idx, c in enumerate(clones):
        try:
            c['od_answer_post_date']
        except:
            print(idx, c['file1'], 'Missing')


def main():

    # TODO: uncomment this if you want to find median or any stats about SO snippets
    # filesizes = get_file_size('/Users/Chaiyong/Downloads/stackoverflow/stackoverflow_formatted')
    # median = statistics.median(filesizes)
    # print('median file size of ' + str(len(filesizes)) + ' = ' + str(median))

    print("A Python script for processing data for Cloverflow study.")
    # copied from
    # https://stackoverflow.com/questions/82831/how-do-i-check-whether-a-file-exists-using-python?page=1&tab=votes#tab-top
    filename = "allclones.list"
    clonefile = Path(filename)

    if not clonefile.exists():
        # download clones
        print("Clone data does not exist. Downloading from the db ...")
        allclones = download_clones()
        write_list_to_file(allclones, filename)
    else:
        allclones = read_list_from_file("allclones.list")

    allclones = clean(allclones)
    print('total clone pairs after removing nulls:', len(allclones))
    # print all the clones to a csv file
    create_csv(allclones)

    # TODO: Uncomment this if you want to see any specific clone pair(s)
    # for i, clone in enumerate(allclones):
    #     if 'QS' in clone['classification'] and '801987' in clone['file1']:
    #         columns = [ 'file1', 'latest_file', 'latest_change_date', 'latest_note', 'code1_license' ]
    #         print(i)
    #         print_a_clone(clone, columns)

    print('-' * 60)
    # print('no. of all clone pairs in the db', len(allclones))

    # get 7 patterns online clone statistics
    filter = "classification"
    classification = "QS"
    qs_uclones, qs_clones = get_unique_so_clones_with_filter(allclones, filter, classification)
    qs_usnippets = get_unique_so_snippets_with_filter(allclones, filter, classification)
    classification = "SQ"
    sq_uclones, sq_clones = get_unique_so_clones_with_filter(allclones, filter, classification)
    sq_usnippets = get_unique_so_snippets_with_filter(allclones, filter, classification)
    classification = "EX"
    ex_uclones, ex_clones = get_unique_so_clones_with_filter(allclones, filter, classification)
    ex_usnippets = get_unique_so_snippets_with_filter(allclones, filter, classification)
    classification = "UD"
    ud_uclones, ud_clones = get_unique_so_clones_with_filter(allclones, filter, classification)
    ud_usnippets = get_unique_so_snippets_with_filter(allclones, filter, classification)
    classification = "BP"
    bp_uclones, bp_clones = get_unique_so_clones_with_filter(allclones, filter, classification)
    bp_usnippets = get_unique_so_snippets_with_filter(allclones, filter, classification)
    classification = "IN"
    in_uclones, in_clones = get_unique_so_clones_with_filter(allclones, filter, classification)
    in_usnippets = get_unique_so_snippets_with_filter(allclones, filter, classification)
    classification = "AC"
    ac_uclones, ac_clones = get_unique_so_clones_with_filter(allclones, filter, classification)
    ac_usnippets = get_unique_so_snippets_with_filter(allclones, filter, classification)

    print("RQ1:")
    print('total clones', len(allclones))
    uclones = get_unique_so_clones(allclones)
    print('total unique clones', len(uclones))
    u_snippets, _ = get_unique_so_snippets(allclones)
    print('total unique snippets', len(u_snippets))
    projects, _ = get_qproject(u_snippets)
    print('qualitas projects', len(projects))
    print('avg. clone ratio', get_avg_clone_ratio(uclones, 1))
    tp_clones = qs_clones + sq_clones + ex_clones + ud_clones + bp_clones + in_clones
    print('total tp clones', len(tp_clones))
    utp = qs_uclones + sq_uclones + ex_uclones + ud_uclones + bp_uclones + in_uclones
    print('total unique tp clones', len(utp))
    tp_snippets = qs_usnippets + sq_usnippets + ex_usnippets + ud_usnippets + bp_usnippets + in_usnippets
    print('total unique tp snippets', len(tp_snippets))
    projects, pcount = get_qproject(utp)
    print('qualitas projects', len(projects))
    print('avg. clone ratio', get_avg_clone_ratio(utp, 1))
    print()
    print('-' * 60)

    print("RQ2:")
    print('no. of SO clones (QS)', len(qs_uclones), '/', len(qs_clones))
    # print('no. of unique SO snippets (' + classification + ')', len(qs_uclones))
    print('no. of SO clones (SQ)', len(sq_uclones), '/', len(sq_clones))
    print('no. of SO clones (EX)', len(ex_uclones), '/', len(ex_clones))
    print('no. of SO clones (UD)', len(ud_uclones), '/', len(ud_clones))
    print('no. of SO clones (BP)', len(bp_uclones), '/', len(bp_clones))
    print('no. of SO clones (IN)', len(in_uclones), '/', len(in_clones))
    print('no. of SO clones (AC)', len(ac_uclones), '/', len(ac_clones))

    projects, pcount = get_qproject(qs_clones)
    print('qualitas projects', len(projects))
    projects, pcount = get_qproject(qs_uclones)
    print('qualitas projects unique', len(projects))

    # TODO: UNCOMMENT IF LATEX TABLE OF 'QS GROUPED BY PROJECTS' IS NEEDED
    print()
    print('QS clone pairs by projects')

    # sort the projects by no. of clone pairs
    # copied from
    # https://stackoverflow.com/questions/6618515/sorting-list-based-on-values-from-another-list
    projects_sorted = [x for _, x in sorted(zip(pcount, projects), reverse=True)]
    pcount_sorted = [x for _, x in sorted(zip(pcount, pcount), reverse=True)]

    for idx, p in enumerate(projects_sorted):
        print(format_project_name(p) + ' & ' + str(pcount_sorted[idx]) + ' \\\\')

    print()
    print('UD clone pairs by projects')
    projects, pcount = get_qproject(ud_uclones)
    print('qualitas projects', len(projects))

    # TODO: UNCOMMENT IF LATEX TABLE OF 'QS GROUPED BY PROJECTS' IS NEEDED
    # copied from
    # https://stackoverflow.com/questions/6618515/sorting-list-based-on-values-from-another-list
    projects_sorted = [x for _, x in sorted(zip(pcount, projects), reverse=True)]
    pcount_sorted = [x for _, x in sorted(zip(pcount, pcount), reverse=True)]

    for idx, p in enumerate(projects_sorted):
        print(format_project_name(p) + ' & ' + str(pcount_sorted[idx]) + ' \\\\')

    # TODO: FOR EX CLONE PAIRS
    print()
    print('analysing EX clone pairs ...')
    print('ex pairs unique', len(ex_uclones))
    clones, allclones = get_unique_so_clones_keyword(ex_uclones, "notes", "ONE-SIDED")
    print('one-sided', len(allclones))
    print('one-sided unique', len(clones))
    # for idx, clone in enumerate(clones):
    #     print(idx, clone['notes'])
    # columns_to_print = [ 'notes' ]
    # file_name = "ex_clones.csv"
    # write_clones_to_file(ex_uclones, columns_to_print, file_name, print_header=True, quote_on=True)
    # print('one-sided unique', len(clones))

    # boxplots
    boxplot(qs_clones, sq_clones, ud_clones, ex_clones, bp_clones, in_clones)
    boxplot_combined(qs_clones, sq_clones, ud_clones, ex_clones, bp_clones, in_clones)
    # boxplot_post_age([qs_clones, ex_clones], ['QS', 'EX'])
    boxplot_post_age([qs_clones], ['QS'])

    print('\nCLONE SIZES:')
    print('Clones & Min & Max & Mean & Median \\\\')
    print('QS', end=' & ')
    stats(get_sizes(qs_clones))
    print('SQ', end=' & ')
    stats(get_sizes(sq_clones))
    print('UD', end=' & ')
    stats(get_sizes(ud_clones))
    print('EX', end=' & ')
    stats(get_sizes(ex_clones))
    print('BP', end=' & ')
    stats(get_sizes(bp_clones))
    print('IN', end=' & ')
    stats(get_sizes(in_clones))

    print()
    print('-' * 60)

    print("RQ3:")
    outdated_clones = get_outdated_clones(qs_uclones)
    print('outdated', len(outdated_clones))
    comment_count, changed = count_od_comment_outdated(outdated_clones)
    print('oudated with comments (yes/no/not found: changed)', comment_count, changed)
    newer, higher_votes = count_newer_higher_votes(outdated_clones)
    print('newer answers', newer)
    print('higher-voted answers (yes/equal)', higher_votes)
    print('intents of changes')
    print(count_outdated_reason(outdated_clones))
    # exit()
    # print_no_date_clones(qs_clones)
    # print_no_date_clones(ex_clones)

    # write outdated clones to a file
    # write_outdated_clones_to_file(outdated_clones)

    # o_projs = get_projects_having_outdated_clones(qs_uclones)
    # OrderDict is suggested by
    # https://stackoverflow.com/questions/613183/how-to-sort-a-dictionary-by-value
    # o_projs_sorted = OrderedDict(sorted(o_projs.items(), key=lambda t: t[1], reverse=True))
    # print(o_projs_sorted)

    # TODO: UNCOMMENT IF THE PLOT 'OUTDATED CODE GROUPED BY PROJECTS" IS NEEDED
    # plot_outdated(o_projs_sorted)

    mod_types = get_code_mod_types(qs_uclones)
    print('mod types', mod_types)
    # TODO: UNCOMMENT IF THE PLOT 'MODIFICATIONS MADE TO OUTDATED CODE' IS NEEDED
    # plot_mod_types(mod_types)

    issues_clones = get_outdated_with_issues(qs_uclones)
    print('no. of unique & outdated SO snippets & having issue', len(issues_clones))
    outdated_clones = get_outdated_clones(qs_uclones)
    print('no. of unique & outdated SO snippets (' + classification + ')', len(outdated_clones))
    projects, pcount = get_qproject(outdated_clones)
    print('no. qualitas projects containing outdated code', len(projects))

    # projects_sorted = [x for _, x in sorted(zip(pcount, projects), reverse=True)]
    # pcount_sorted = [x for _, x in sorted(zip(pcount, pcount), reverse=True)]
    #
    # for idx, p in enumerate(projects_sorted):
    #     print(format_project_name(p) + ' & ' + str(pcount_sorted[idx]) + ' \\\\')
    #
    # # print outdated clones to a file
    # file_name = "outdated_clones.csv"
    # # columns_to_print = ["file1", "start1", "end1",
    # #                     "latest_change_ad", "latest_change_md", "latest_change_rm",
    # #                     "latest_change_rw", "latest_change_ap", "latest_deleted"]
    # columns_to_print = ["file1", "start1", "end1"]
    # write_clones_to_file(outdated_clones, columns_to_print, file_name, print_header=True, quote_on=False)

    print()
    print('-' * 60)

    print('RQ4:')
    print('license analysis using Ninka')

    ## TODO: UNCOMMENT IF YOU NEED TO UPDATE THE LICENSE INFO ON THE DB
    # update_license('QS', allclones)
    # update_license('EX', allclones)
    # update_license('UD', allclones)
    # update_license('BP', allclones)
    # update_license('IN', allclones)
    # update_license('AC', allclones)

    qs_usnippets, _ = get_unique_so_snippets(qs_uclones)
    delete_file('clone_licenses.csv')
    print('>> QS (', len(qs_usnippets), ')')
    qs_licenses = get_license("QS", qs_usnippets)
    for key, value in qs_licenses.items():
        print(key + ' & ' + str(value) + ' \\\\ ')
    print()

    ex_usnippets, _ = get_unique_so_snippets(ex_uclones)
    print('>> EX (', len(ex_usnippets), ')')
    ex_licenses = get_license("EX", ex_usnippets)
    for key, value in ex_licenses.items():
        print(key + ' & ' + str(value) + ' \\\\ ')
    print()

    ud_usnippets, _ = get_unique_so_snippets(ud_uclones)
    print('>> UD (', len(ud_usnippets), ')')
    ud_licenses = get_license("UD", ud_usnippets)
    for key, value in ud_licenses.items():
        print(key + ' & ' + str(value) + ' \\\\ ')
    print()


main()