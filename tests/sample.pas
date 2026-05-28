! ============================================================
! Sample DSL Program: Bubble Sort + Factorial + Fibonacci
! Demonstrates: variables, arrays, functions, procedures,
!               if/else, while loops, read/write
! ============================================================
program SampleProgram;

var
    n, i, j, temp : integer;
    result        : integer;
    arr           : array[1..10] of integer;

! ── Factorial function ──────────────────────────────────────
function factorial(num : integer) : integer;
var
    f : integer;
begin
    if num <= 1 then
        f := 1
    else
        f := num * factorial(num - 1);
    factorial := f
end;

! ── Bubble sort procedure ────────────────────────────────────
procedure bubbleSort(size : integer);
var
    swapped : integer;
    k, m    : integer;
begin
    k := 1;
    while k < size do
    begin
        m := 1;
        while m < size - k + 1 do
        begin
            if arr[m] > arr[m + 1] then
            begin
                temp       := arr[m];
                arr[m]     := arr[m + 1];
                arr[m + 1] := temp
            end;
            m := m + 1
        end;
        k := k + 1
    end
end;

! ── Main program ────────────────────────────────────────────
begin
    write('Enter n (1-10): ');
    read(n);

    ! Read array elements
    i := 1;
    while i <= n do
    begin
        write('arr[');
        write(i);
        write(']: ');
        read(arr[i]);
        i := i + 1
    end;

    ! Compute factorial of n
    result := factorial(n);
    write('Factorial of ');
    write(n);
    write(' = ');
    write(result);

    ! Sort the array
    bubbleSort(n);

    ! Print sorted array
    write('Sorted array: ');
    i := 1;
    while i <= n do
    begin
        write(arr[i]);
        i := i + 1
    end
end.
