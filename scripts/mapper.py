import pandas as pd

def mapp():
    file1 = '/home/edotacca/working_dir/ena-submission/data/FEAMP20/runs.txt'

    with open(file1,'r')as reader:
        lines = reader.readlines()

        dict_runs = {}

        for line in lines:
            split_lines = line.strip('\n').split('\t')
            run_id = split_lines[0]
            file_name = split_lines[1]
            check_sum = split_lines[4]

            listina = [file_name,check_sum]

            if run_id not in dict_runs:
                dict_runs[run_id] = listina
            elif run_id in dict_runs:
                dict_runs[run_id].extend(listina)

    print(list(dict_runs.items())[:1])
    print('--------------------------')
    file2 = '/home/edotacca/working_dir/ena-submission/data/FEAMP20/FEAMP20_samples.txt'

    with open(file2,'r') as reader2:
        lines = reader2.readlines()

        dict_reports = {}

        for line in lines[1:]:
            line_l = line.strip('\n').split('\t')
            run_id = line_l[0]
            biosample = line_l[1]
            title = line_l[2]

            listarella = [title,biosample]

            dict_reports[run_id] = listarella

    print(list(dict_reports.items())[:1])
    print('--------------------------')
    file3 = '/home/edotacca/working_dir/ena-submission/data/FEAMP20/FEAMP_ena_16S.txt'

    with open(file3,'r')as reader3:
        lines = reader3.readlines()

        dict_exp = {}
        for line in lines:
            line_l = line.strip('\n').split('\t')
            run_id = line_l[0]
            sample = line_l[3]
            exp_acc = line_l[4]
        
            lista = [run_id,exp_acc]
            dict_exp[sample] = lista
    print(list(dict_exp.items())[:1])

    not_g = 'Not_retrieved'
    rows = []
    for key,values in dict_reports.items():
        
        if key in dict_exp.keys():
            exp = dict_exp[key]
            run_id = exp[0]

            if run_id in dict_runs.keys():
                run = dict_runs[run_id]
            else:
                run = ['Not_found','Not_found','Not_found','Not_found']



            row = pd.Series({
                        "sample_alias":values[0] ,     # Custom
                        "sample_id_paper": values[1],  # SAMEA
                        "sample_accession": key,
                        "experiment_alias": not_g,
                        "experiment_accession":exp[1],
                        "run_alias": not_g,
                        "run_accession": run_id,
                        "forward_file": run[2],
                        "reverse_file": run[0],
                        "forward_checksum": run[3],
                        "reverse_checksum": run[1]
            }).to_frame().T

        print(row)
        rows.append(row)

    data = pd.concat(rows)

    columns = ['sample_alias','sample_id_paper','sample_accession',
            'experiment_alias',	'experiment_accession',	'run_alias','run_accession',
            'forward_file','reverse_file','forward_checksum','reverse_checksum']
    
    dataframe = pd.DataFrame(data=data,columns=columns)
    print(data)

    return data







mapp()