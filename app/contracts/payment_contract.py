# /imanipay-blockchain-service/app/contracts/payment_contract.py
from pyteal import Txn, Assert, Int, TxnType, Seq, Return, compileTeal, Mode, InnerTxnBuilder, Global, Addr, TxnField, Btoi

def payment_contract():
    """
    This contract handles a basic payment from a sender to a receiver, with a fee.
    The sender covers both the payment amount and the fee.
    """
    # Get the sender, receiver, amount, and fee from the transaction arguments.
    sender = Txn.sender()
    receiver = Btoi(Txn.application_args[0])  # Receiver address from bytes
    amount = Btoi(Txn.application_args[1])
    fee_amount = Btoi(Txn.application_args[2])
    # NEW: Define the owner's address (replace with the actual address)
    owner_address = Addr("UYG2YF4QUYJGNQQ4D5HIOM7376WIJ5NURU7JV77VHOMTCRQZROMCWNX6KM")
    # NEW: Check if the sender is the owner
    is_owner = Assert(sender == owner_address)
    # Basic checks:
    # 1. Ensure the amount is positive.
    amount_check = Assert(amount > Int(0))
    # 2. Ensure the fee is not negative.
    fee_check = Assert(fee_amount >= Int(0))
    # 3. Ensure that the transaction is a PaymentTxn
    txn_type_check = Assert(Txn.type_enum() == TxnType.Payment)
    # Send the payment. The contract sends the 'amount' to the receiver.
    payment_txn = Seq([
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetField(TxnField.type_enum, TxnType.Payment),
        InnerTxnBuilder.SetField(TxnField.receiver, receiver),
        InnerTxnBuilder.SetField(TxnField.amount, amount),
        InnerTxnBuilder.Submit(),
    ])
    # Define the program flow
    program = Seq([
        is_owner,  # NEW: Add the ownership check to the sequence
        amount_check,
        fee_check,
        txn_type_check,
        payment_txn,
        Return(Int(1)),  # Return 1 on success
    ])
    return program

def clear_state_program():
    """
    A simple clear state program that allows the sender to clear their state.
    """
    return Return(Int(1))

if __name__ == "__main__":
    # Compile the programs.
    approval_teal = compileTeal(payment_contract(), Mode.Application, version=6)
    clear_teal = compileTeal(clear_state_program(), Mode.Application, version=6)

    # Specify the file paths.
    approval_file_path = "approval.teal"
    clear_file_path = "clear.teal"

    # Write the Teal code to files.
    try:
        with open(approval_file_path, "w") as f:
            f.write(approval_teal)
        print(f"Approval Program Teal written to: {approval_file_path}")

        with open(clear_file_path, "w") as f:
            f.write(clear_teal)
        print(f"Clear State Program Teal written to: {clear_file_path}")

    except Exception as e:
        print(f"An error occurred while writing to files: {e}")

    # You can still print to the terminal if you want:
    # print("\nApproval Program:")
    # print(approval_teal)
    # print("\nClear State Program:")
    # print(clear_teal)



    # Example Usage (outside the contract):
    # 1.  The sender decides: amount = 10, fee = 1.
    # 2.  The sender sends a transaction with:
    #     -   amount + fee (11) as the transaction amount.
    #     -   A call to the smart contract with:
    #         -   app_call_txn.fee = calculated fee
    #         -   app_call_txn.application_args = [receiver_address, 10, 1]
    # 3.  The smart contract's InnerTransaction sends 10 to the receiver.
    # 4.  The sender's account is debited 11 (10 + 1).
    # 5.  The receiver's account is credited 10.