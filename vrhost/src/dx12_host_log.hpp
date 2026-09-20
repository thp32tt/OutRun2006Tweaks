#pragma once

#include <fstream>
#include <iostream>
#include <streambuf>

namespace OutRunVRHostDX12
{
    class TeeStreamBuf final : public std::streambuf
    {
    public:
        TeeStreamBuf(std::streambuf* first,std::streambuf* second) noexcept
            : first_(first),second_(second) {}

    protected:
        int overflow(int ch) override
        {
            if(traits_type::eq_int_type(ch,traits_type::eof()))
                return traits_type::not_eof(ch);
            const char c=traits_type::to_char_type(ch);
            const auto a=first_?first_->sputc(c):ch;
            const auto b=second_?second_->sputc(c):ch;
            if((first_&&traits_type::eq_int_type(a,traits_type::eof()))||
               (second_&&traits_type::eq_int_type(b,traits_type::eof())))
                return traits_type::eof();
            return ch;
        }

        std::streamsize xsputn(
            const char* s,std::streamsize count) override
        {
            const auto a=first_?first_->sputn(s,count):count;
            const auto b=second_?second_->sputn(s,count):count;
            return (a==count&&b==count)?count:0;
        }

        int sync() override
        {
            const int a=first_?first_->pubsync():0;
            const int b=second_?second_->pubsync():0;
            return (a==0&&b==0)?0:-1;
        }

    private:
        std::streambuf* first_{};
        std::streambuf* second_{};
    };

    class ScopedHostLog final
    {
    public:
        explicit ScopedHostLog(
            const char* fileName="outrun-vr-host-dx12.log")
            : file_(fileName,std::ios::out|std::ios::trunc),
              outTee_(std::cout.rdbuf(),file_.is_open()?file_.rdbuf():nullptr),
              errTee_(std::cerr.rdbuf(),file_.is_open()?file_.rdbuf():nullptr)
        {
            oldOut_=std::cout.rdbuf(&outTee_);
            oldErr_=std::cerr.rdbuf(&errTee_);
            std::cout.setf(std::ios::unitbuf);
            std::cerr.setf(std::ios::unitbuf);
        }

        ScopedHostLog(const ScopedHostLog&)=delete;
        ScopedHostLog& operator=(const ScopedHostLog&)=delete;

        ~ScopedHostLog()
        {
            std::cout.flush();
            std::cerr.flush();
            if(oldOut_)std::cout.rdbuf(oldOut_);
            if(oldErr_)std::cerr.rdbuf(oldErr_);
            if(file_.is_open())file_.flush();
        }

        bool FileOpen() const noexcept { return file_.is_open(); }

    private:
        std::ofstream file_;
        TeeStreamBuf outTee_;
        TeeStreamBuf errTee_;
        std::streambuf* oldOut_{};
        std::streambuf* oldErr_{};
    };
}
