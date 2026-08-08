import numpy as np


def main() -> None:
    arr = np.genfromtxt("./name_age_sex_data.csv", delimiter=",", dtype="U7")
    print(arr[:5])

    # Transpose the array
    transposed_arr = arr.transpose()
    print(transposed_arr)

    # slicing names
    names = transposed_arr[0:1, 1:]
    print(names)

    # slicing ages
    ages = transposed_arr[2:3, 1:]
    print(ages)

    # slicing sex
    sex = transposed_arr[1:2, 1:]
    print(sex)

    # aged 56
    aged_56 = names[ages.astype(int) == 56]
    print(aged_56)

    # people under 44
    # using boolean slicing to access names
    under_44_age = names[ages.astype(int) <= 44]
    print(under_44_age)

    # Using shape attribute to find people under 44
    under_44_shape = np.shape(under_44_age)
    print(f"Number of people under 44: {under_44_shape[0]}")

    # Names of males
    males = names[sex == "Male"]
    print(males)

    males_number_in_array = np.shape(males)
    print(f"Number of males: {males_number_in_array[0]}")

    # Avg age of Females
    # converting age data to int
    ages_int = ages.astype(int)

    # Calculate the average age of females
    #
    average_age_f = ages_int[sex == "Female"].mean()
    print(f"Average age of females: {average_age_f}")

    # Calculate the average age of people named Olivia and Kate
    olivia_age = ages_int[names == "Olivia"]
    kate_age = ages_int[names == "Kate"]

    average = np.array([olivia_age, kate_age]).mean()
    print(f"Average age of Olivia and Kate: {average}")
